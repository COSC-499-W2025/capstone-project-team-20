from __future__ import annotations

import signal
import json
import os
import sys
import re
import shutil
import contextlib
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Dict, Any

from datetime import datetime

from src.project_timeline import (
    get_projects_with_skills_timeline_from_projects,
    get_skill_timeline_from_projects,
)
from src.analyzers.badge_engine import (
    ProjectAnalyticsSnapshot,
    assign_badges,
    build_fun_facts,
)

from src.ZipParser import parse, toString, extract_zip
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.FileCategorizer import FileCategorizer
from src.analyzers.language_detector import detect_language_per_file, analyze_language_share
from src.analyzers.ContributionAnalyzer import ContributionAnalyzer, ContributionStats
from utils.RepoFinder import RepoFinder
from src.ProjectManager import ProjectManager
from src.Project import Project
from src.analyzers.SkillAnalyzer import SkillAnalyzer
from src.generators.ResumeInsightsGenerator import ResumeInsightsGenerator
from src.ConfigManager import ConfigManager
from src.ProjectRanker import ProjectRanker
from src.analyzers.RepoProjectBuilder import RepoProjectBuilder
from utils.set_variables_analysis import set_project_analysis_values

MIN_DISPLAY_CONFIDENCE = 0.5  # only show skills with at least this confidence


class ProjectAnalyzer:
    """
    Unified interface for analyzing zipped project files.
    Responsibilities:
    1. Git repo analysis + contribution share
    2. Metadata and file statistics
    3. File categorization
    4. Folder tree printing
    5. Language detection
    6. Run all analyses
    7. Analyze New Folder
    8. Change Selected Users
    9. Analyze Skills
    10. Generate Resume
    11. Display Previous Results
    12. Exit
    """

    def __init__(self, config_manager: ConfigManager):
        self.root_folder = None
        self.zip_path: Optional[Path] = None
        self._config_manager = config_manager

        self.metadata_extractor = ProjectMetadataExtractor(self.root_folder)
        self.file_categorizer = FileCategorizer()
        self.repo_finder = RepoFinder()
        self.project_manager = ProjectManager()
        self.contribution_analyzer = ContributionAnalyzer()

        # Caches used primarily for resume insight generation
        self.cached_extract_dir: Optional[Path] = None
        self.cached_projects: Optional[Iterable[Project]] = None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @contextlib.contextmanager
    def suppress_output(self):
        """Temporarily suppress stdout and stderr."""
        with open(os.devnull, "w") as devnull:
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = devnull
            sys.stderr = devnull
            try:
                yield
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

    def load_or_create_project(self) -> Project:
        name = Path(self.zip_path).stem
        project = self.project_manager.get_by_name(name)
        if project is None:
            project = Project(
                name=name,
                file_path=str(self.zip_path),
                root_folder=str(self.root_folder.name if self.root_folder else ""),
            )
        return project

    def _print_project(self, project: Project) -> None:
        print(f"Project: {project.name}")
        print("-" * (len(project.name) + 9))
        print(f"  - Authors ({project.author_count}): {', '.join(project.authors)}")
        print(f"  - Status: {project.collaboration_status}\n")

    def clean_path(self, raw_input: str) -> Path:
        stripped = raw_input.strip()
        # Only strip quotes that surround path (so that something like `dylan's.zip` does not break the parser)
        if (stripped.startswith('"') and stripped.endswith('"')) or \
           (stripped.startswith("'") and stripped.endswith("'")):
            stripped = stripped[1:-1]

        # On Windows, treat the input literally (backslashes are part of the path)
        if os.name == "nt":
            return Path(os.path.expanduser(stripped))

        # On POSIX shells, allow escaping spaces etc. ("my\ file.zip" -> "my file.zip")
        unescaped = re.sub(r'\\(.)', r'\1', stripped)
        return Path(os.path.expanduser(unescaped))

    # ------------------------------------------------------------------
    # Batch & ZIP loading
    # ------------------------------------------------------------------

    def batch_analyze(self, zipped_repos_dir: str = "zipped_repos") -> None:
        """
        Loops through all zipped repositories in a directory (`zipped_repos/` by default)
        and calls run_all(). Called from utils/analyze_repos.py
        """
        zipped_repos_path = Path(zipped_repos_dir)
        if not zipped_repos_path.exists():
            print(f"Nothing to analyze - {zipped_repos_dir}/ doesn't exist")
            return

        zip_files = list(zipped_repos_path.rglob("*.zip"))
        if not zip_files:
            print(f"No .zip files found in {zipped_repos_dir}/")
            return

        print(f"\nBatch analyzing {len(zip_files)} repositories...\n")
        analyzed, failed = 0, 0

        for zip_path in zip_files:
            repo_name = zip_path.stem
            try:
                self.zip_path = Path(zip_path)
                self.root_folder = parse(self.zip_path)
                self.metadata_extractor = ProjectMetadataExtractor(self.root_folder)
                print(f"\n{'=' * 50}")
                print(f"Analyzing: {repo_name}")
                print(f"{'=' * 50}")
                self.run_all()
                analyzed += 1

            except Exception as e:
                print(f"❌ {repo_name}: {str(e)[:50]}")
                failed += 1

        print(f"\n{'=' * 40}")
        print(f"Analyzed: {analyzed} | Failed: {failed}")
        print(f"{'=' * 40}\n")

    def load_zip(self) -> bool:
        """Prompts user for ZIP file and parses into folder tree."""
        zip_path = self.clean_path(input("Please enter the path to the zipped folder: "))
        while not (os.path.exists(zip_path) and zipfile.is_zipfile(zip_path)):
            zip_path = self.clean_path(input("Invalid path or not a zipped file. Please try again: "))

        self.zip_path = zip_path
        print("Parsing ZIP structure...")
        try:
            self.root_folder = parse(zip_path)
            print("Project parsed successfully...\n")
        except Exception as e:
            print(f"Error while parsing: {e}")
            return False

        self.metadata_extractor = ProjectMetadataExtractor(self.root_folder)
        return True

    # ------------------------------------------------------------------
    # Project Initialization using RepoProjectBuilder
    # ------------------------------------------------------------------

    def initialize_projects(self) -> List[Project]:
        """
        Uses RepoProjectBuilder to find all repos, create Project objects,
        and saves them to the database. This is the single source of truth
        for project creation.
        Returns a list of the created/updated project objects.
        """
        print("\n--- Initializing Project Records ---")
        if not self.zip_path or not self.root_folder:
            print("No project loaded. Please load a zip file first.\n")
            return []

        temp_dir = Path(extract_zip(str(self.zip_path)))
        builder = RepoProjectBuilder(self.root_folder)

        created_projects: List[Project] = []
        try:
            projects_from_builder = builder.scan(temp_dir)
            if not projects_from_builder:
                print("No Git repositories found to build projects from.")
                # If no repos found, treat the whole zip as one project
                project_name = self.zip_path.stem
                proj_existing = self.project_manager.get_by_name(project_name)
                if not proj_existing:
                    proj_new = Project(name=project_name, file_path=str(temp_dir))
                    self.project_manager.set(proj_new)
                    print(f"  - Created new project record: {proj_new.name} with ID {proj_new.id}")
                    return [proj_new]
                return [proj_existing]

            print(f"Found {len(projects_from_builder)} project(s). Saving initial records...")
            for proj_new in projects_from_builder:
                proj_existing = self.project_manager.get_by_name(proj_new.name)
                if proj_existing:
                    # If it exists, update it with basic info from the builder
                    proj_existing.authors = proj_new.authors
                    proj_existing.author_count = len(proj_new.authors)
                    self.project_manager.set(proj_existing)
                    print(f"  - Updated existing project: {proj_existing.name}")
                    created_projects.append(proj_existing)
                else:
                    # Save the newly created project
                    self.project_manager.set(proj_new)
                    print(f"  - Created new project record: {proj_new.name} with ID {proj_new.id}")
                    created_projects.append(proj_new)
            return created_projects
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Git & contribution analysis
    # ------------------------------------------------------------------

    def _prompt_for_usernames(self, authors: List[str]) -> Optional[List[str]]:
        """
        Prompts user to select multiple usernames from a list of contributors.
        """
        print("\nPlease select your username(s) from the list of project contributors:")
        if not authors:
            print("No authors found in the commit history.")
            return None

        for i, author in enumerate(authors):
            print(f"  {i + 1}: {author}")

        print("\nYou can select multiple authors by entering numbers separated by commas (e.g., 1, 3).")

        try:
            choice_str = input("Enter your choice(s) (or 'q' to quit): ").strip()

            if choice_str.lower() == "q":
                print("Aborting user selection.")
                return None

            selected_authors: List[str] = []
            choices = [c.strip() for c in choice_str.split(",")]
            for choice in choices:
                if not choice.isdigit():
                    print(f"Invalid input '{choice}'. Please use numbers only.")
                    return self._prompt_for_usernames(authors)

                index = int(choice) - 1
                if 0 <= index < len(authors):
                    selected_authors.append(authors[index])
                else:
                    print(f"Invalid number '{choice}'. Please try again.")
                    return self._prompt_for_usernames(authors)

            return sorted(list(set(selected_authors)))
        except ValueError:
            print("Invalid input format. Please enter numbers separated by commas.")
            return self._prompt_for_usernames(authors)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return None

    def _get_or_select_usernames(self, authors: List[str]) -> Optional[List[str]]:
        """
        Retrieves configured usernames or prompts the user to select them.
        """
        usernames = self._config_manager.get("usernames")
        if usernames and isinstance(usernames, list):
            print(f"\nWelcome back! Analyzing contributions for: {', '.join(usernames)}")
            return usernames

        if authors:
            print("\nNo usernames found in configuration. Let's set them up.")
            new_usernames = self._prompt_for_usernames(authors)
            if new_usernames:
                self._config_manager.set("usernames", new_usernames)
                print(f"Usernames '{', '.join(new_usernames)}' have been saved.")
                return new_usernames

        print("No authors found or selected. Skipping contribution analysis.")
        return None

    def _aggregate_stats(
        self,
        author_stats: Dict[str, ContributionStats],
        selected_authors: Optional[List[str]] = None,
    ) -> ContributionStats:
        """
        Aggregates ContributionStats from a dictionary. If selected_authors
        is provided, it aggregates only for those authors. Otherwise, it
        aggregates for all authors in the dictionary.
        """
        aggregated = ContributionStats()
        authors_to_aggregate = selected_authors if selected_authors is not None else author_stats.keys()

        for author in authors_to_aggregate:
            if author in author_stats:
                stats = author_stats[author]
                aggregated.lines_added += stats.lines_added
                aggregated.lines_deleted += stats.lines_deleted
                aggregated.total_commits += stats.total_commits
                aggregated.files_touched.update(stats.files_touched)
                for category, count in stats.contribution_by_type.items():
                    aggregated.contribution_by_type[category] += count
        return aggregated

    def _display_contribution_results(
        self,
        selected_stats: ContributionStats,
        total_stats: ContributionStats,
        usernames: List[str],
    ) -> None:
        """Formats and prints the aggregated contribution analysis results."""

        header = f"Contribution Share for: {', '.join(usernames)}"
        print("\n" + "=" * 80)
        print(f"{header:^80}")
        print("=" * 80)

        total_lines_edited_project = total_stats.lines_added + total_stats.lines_deleted
        total_lines_edited_selected = selected_stats.lines_added + selected_stats.lines_deleted

        if total_lines_edited_project > 0:
            project_share = (total_lines_edited_selected / total_lines_edited_project) * 100
            print(f"\nCollectively, you built {project_share:.2f}% of the codebase for this project.")
        else:
            print("\nNo line changes were found in the project to calculate contribution share.")

        print("\n--- Combined Statistics for Selected Users ---")
        print(f"  Total Commits: {selected_stats.total_commits}")
        print(f"  Files Touched: {len(selected_stats.files_touched)}")
        print(f"  Lines Added:   {selected_stats.lines_added}")
        print(f"  Lines Deleted: {selected_stats.lines_deleted}")

        total_lines_by_type = sum(selected_stats.contribution_by_type.values())
        if total_lines_by_type > 0:
            print("  Contribution Share by Type:")
            for type_name, count in selected_stats.contribution_by_type.items():
                percentage = (count / total_lines_by_type) * 100
                print(f"    - {type_name.capitalize():<5}: {percentage:6.2f}%")
        print("\n" + "=" * 80)

    def analyze_git_and_contributions(self) -> None:
        """
        Orchestrates the Git analysis workflow by running a single comprehensive
        analysis and then processing the results.
        """
        print("\n--- Git Repository & Contribution Analysis ---")
        if not self.zip_path:
            print("No project loaded. Please load a zip file first.\n")
            return

        path_obj = Path(self.zip_path)
        if not path_obj.exists() or path_obj.suffix.lower() != ".zip":
            print(f"Error: {path_obj} is not a valid zip file.")
            return

        temp_dir = extract_zip(str(path_obj))
        try:
            repo_paths = self.repo_finder.find_repos(temp_dir)
            if not repo_paths:
                print("No Git repositories found in the provided ZIP.")
                return

            repo_path = str(repo_paths[0])

            # Step 1: Efficiently get all author names.
            all_authors_list = self.contribution_analyzer.get_all_authors(repo_path)

            # Step 2: Handle user selection.
            usernames = self._get_or_select_usernames(all_authors_list)

            if usernames:
                # Step 3: Run the full analysis only if needed.
                all_author_stats = self.contribution_analyzer.analyze(repo_path)
                selected_stats = self._aggregate_stats(all_author_stats, usernames)
                total_stats = self._aggregate_stats(all_author_stats)

                # Step 4: Display the results.
                self._display_contribution_results(selected_stats, total_stats, usernames)

                # Step 5: Persist authors & contributions into the Project row
                try:
                    project = self._get_or_create_project_record()
                except RuntimeError:
                    project = None

                if project is not None:
                    # All authors seen in the repo
                    project.authors = sorted(set(all_authors_list))
                    project.author_count = len(project.authors)

                    # Collaboration status ("individual" / "collaborative")
                    project.collaboration_status = (
                        "individual" if project.author_count <= 1 else "collaborative"
                    )

                    # Per-author contributions snapshot
                    contributions: List[Dict[str, Any]] = []
                    for author, stats in all_author_stats.items():
                        contributions.append(
                            {
                                "author": author,
                                "lines_added": stats.lines_added,
                                "lines_deleted": stats.lines_deleted,
                                "total_commits": stats.total_commits,
                                "files_touched": sorted(stats.files_touched),
                                "contribution_by_type": dict(stats.contribution_by_type),
                            }
                        )

                    project.author_contributions = contributions

                    # Overall share for the selected users
                    try:
                        share = self.contribution_analyzer.calculate_share(
                            selected_stats, total_stats
                        )
                    except Exception:
                        share = None
                    project.individual_contributions = share

                    project.last_accessed = datetime.now()
                    self.project_manager.set(project)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def change_selected_users(self) -> None:
        """Allows the user to change their configured username selection."""
        print("\n--- Change Selected Users ---")
        if not self.zip_path:
            print("No project loaded. Please load a zip file first.\n")
            return

        path_obj = Path(self.zip_path)
        if not path_obj.exists() or path_obj.suffix.lower() != ".zip":
            print(f"Error: {path_obj} is not a valid zip file.")
            return

        temp_dir = extract_zip(str(path_obj))
        try:
            repo_paths = self.repo_finder.find_repos(temp_dir)
            if not repo_paths:
                print("No Git repositories found in the provided ZIP.")
                return

            # Get the current list of authors to present to the user.
            all_authors_list = self.contribution_analyzer.get_all_authors(str(repo_paths[0]))

            print("Please select the new set of usernames you would like to use.")
            new_usernames = self._prompt_for_usernames(all_authors_list)

            if new_usernames:
                self._config_manager.set("usernames", new_usernames)
                print(f"\nSuccessfully updated selected users to: {', '.join(new_usernames)}")
            else:
                print("\nNo changes made to user selection.")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Metadata, categories, languages
    # ------------------------------------------------------------------

    def analyze_metadata(self) -> None:
        print("\nMetadata & File Statistics:")
        metadata_full = self.metadata_extractor.extract_metadata() or {}
        project_meta = metadata_full.get("project_metadata", {}) or {}

        try:
            project = self._get_or_create_project_record()
        except RuntimeError:
            # No zip loaded; nothing to persist
            return

        # Authors (list or comma-separated string)
        authors = project_meta.get("authors")
        if isinstance(authors, list):
            project.authors = authors
        elif isinstance(authors, str):
            parts = [a.strip() for a in authors.split(",") if a.strip()]
            project.authors = parts

        if project.authors:
            project.author_count = len(project.authors)

        # Collaboration status if extractor infers it
        collab_status = project_meta.get("collaboration_status")
        if isinstance(collab_status, str):
            project.collaboration_status = collab_status

        # Basic size metrics from metadata if present
        num_files = project_meta.get("total_files") or project_meta.get("num_files")
        if num_files is not None:
            try:
                project.num_files = int(num_files)
            except (TypeError, ValueError):
                pass

        size_kb = project_meta.get("total_size_kb") or project_meta.get("size_kb")
        if size_kb is not None:
            try:
                project.size_kb = int(size_kb)
            except (TypeError, ValueError):
                pass

        # timestamps
        start_raw = project_meta.get("start_date")
        end_raw = project_meta.get("end_date")
        try:
            if start_raw:
                project.date_created = datetime.fromisoformat(str(start_raw))
            if end_raw:
                project.last_modified = datetime.fromisoformat(str(end_raw))
        except Exception:
            pass

        # Touch last_accessed
        project.last_accessed = datetime.now()
        self.project_manager.set(project)

    def analyze_categories(self) -> None:
        print("File Categories")
        files = self.metadata_extractor.collect_all_files()
        file_dicts = [
            {"path": f.file_name, "language": getattr(f, "language", "Unknown")}
            for f in files
        ]
        result = self.file_categorizer.compute_metrics(file_dicts)

        project = self.load_or_create_project()
        project.categories = result
        self.project_manager.set(project)

        print(result)

    def print_tree(self) -> None:
        print("Project Folder Structure")
        print(toString(self.root_folder))

    def analyze_languages(self) -> None:
        print("Language Detection")
        files = self.metadata_extractor.collect_all_files()
        langs = set()

        for f in files:
            lang = detect_language_per_file(Path(f.file_name))
            if lang:
                langs.add(lang)

        if not langs:
            print("No languages detected")
            return

        for lang in sorted(langs):
            print(f" - {lang}")

        # Persist detected languages onto the Project row
        project = self.load_or_create_project()
        project.languages = sorted(list(langs))
        self.project_manager.set(project)

    # ------------------------------------------------------------------
    # Project persistence helpers
    # ------------------------------------------------------------------

    def _get_or_create_project_record(self) -> Project:
        """
        Fetch the Project row for the currently loaded ZIP, or create an
        in-memory Project with baseline information (paths, counts, dates).

        The caller is responsible for calling self.project_manager.set(project)
        after updating any additional fields.
        """
        if not self.zip_path:
            raise RuntimeError("No zip_path set; cannot create Project record.")

        project_name = Path(self.zip_path).stem
        project = self.project_manager.get_by_name(project_name)

        if project is not None:
            return project

        # New project record: fill baseline info
        num_files = 0
        if self.root_folder and self.metadata_extractor:
            try:
                num_files = len(self.metadata_extractor.collect_all_files())
            except Exception:
                num_files = 0

        size_kb = 0
        try:
            size_kb = int(self.zip_path.stat().st_size / 1024)
        except Exception:
            pass

        # Use filesystem timestamps as a reasonable proxy for dates
        try:
            stat = self.zip_path.stat()
            created_dt = datetime.fromtimestamp(stat.st_ctime)
            modified_dt = datetime.fromtimestamp(stat.st_mtime)
        except Exception:
            created_dt = None
            modified_dt = None

        project = Project(
            name=project_name,
            file_path=str(self.zip_path),
            root_folder=str(self.root_folder or ""),
            num_files=num_files,
            size_kb=size_kb,
            date_created=created_dt,
            last_modified=modified_dt,
            last_accessed=datetime.now(),
        )

        return project

    # ------------------------------------------------------------------
    # Skill analysis (CodeMetrics + SkillAnalyzer + persistence)
    # ------------------------------------------------------------------

    def analyze_skills(self) -> None:
        """
        Run skill analysis on all projects in the database.

        This:
        - Extracts the zip to a temporary directory,
        - Runs SkillAnalyzer for each project (which internally runs CodeMetricsAnalyzer),
        - Enriches project objects with metrics, tech-profile flags, and scores,
        - Persists the enriched projects to the database,
        - Prints a human-readable summary of detected skills and metrics for each project.
        """
        if not self.zip_path:
            print("No project loaded.\n")
            return

        print("\n--- Enriching Projects with Skill Analysis & Scoring ---")

        projects_to_analyze = self.project_manager.get_all()
        project_list = list(projects_to_analyze)

        if not project_list:
            print("No projects found in the database. Please run 'Initialize/Re-scan Projects' first.")
            return

        if not self.zip_path.exists() or not zipfile.is_zipfile(self.zip_path):
            print(f"Error: {self.zip_path} is not a valid zip file.")
            return

        temp_dir = Path(extract_zip(str(self.zip_path)))
        try:
            for project in project_list:
                print(f"\nAnalyzing skills for: {project.name}...")

                # Flexible path finding: check for a subdirectory, fall back to root
                project_source_path = temp_dir / project.name
                if not project_source_path.exists():
                    print(
                        f"  - Warning: Source path '{project_source_path}' not found. "
                        "Analyzing root of zip instead."
                    )
                    project_source_path = temp_dir

                skill_analyzer = SkillAnalyzer(project_source_path)
                result = skill_analyzer.analyze()

                skills = result.get("skills") or []
                stats = result.get("stats") or {}
                dimensions = result.get("dimensions") or {}
                tech_profile = result.get("tech_profile") or {}

                if not stats:
                    print(f"  - No metrics could be inferred for {project.name}.")
                    continue

                overall = stats.get("overall", {}) or {}
                per_lang = stats.get("per_language", {}) or {}

                # --- Use helper to push stats + tech profile into Project fields ---
                set_project_analysis_values(
                    project=project,
                    stats=stats,
                    dimensions=dimensions,
                    tech_profile=tech_profile,
                )

                # --- Filter skills by confidence for display & persistence ---
                filtered_skills: List[Tuple[str, float]] = []
                for item in skills:
                    if isinstance(item, dict):
                        name = item.get("skill") or item.get("name")
                        conf = item.get("confidence", 1.0)
                    else:
                        name = getattr(item, "skill", None) or getattr(item, "name", None)
                        conf = getattr(item, "confidence", 1.0)

                    if name and conf >= MIN_DISPLAY_CONFIDENCE:
                        filtered_skills.append((name.strip(), conf))

                seen = set()
                deduped_skill_names: List[str] = []
                for name, _ in filtered_skills:
                    key = name.lower()
                    if key not in seen:
                        seen.add(key)
                        deduped_skill_names.append(name)

                project.skills_used = deduped_skill_names

                # Update timestamps
                project.last_modified = datetime.now()
                project.last_accessed = datetime.now()

                # Calculate the final score
                ranker = ProjectRanker(project)
                ranker.calculate_resume_score()

                # --- Save the fully enriched object back to the database ---
                self.project_manager.set(project)
                print(f"  - Successfully enriched and saved '{project.name}'.")
                print(f"  - Final Resume Score: {project.resume_score:.2f}")

                # --- Display detailed analysis results ---
                print("\n  Project-level code metrics:")
                if not overall:
                    print("    (no metrics available)")
                else:
                    for k, v in overall.items():
                        print(f"    - {k}: {v}")

                print("\n  Per-language metrics:")
                if per_lang:
                    for lang, data in per_lang.items():
                        print(f"    - {lang}:")
                        for k_lang, v_lang in data.items():
                            print(f"        {k_lang}: {v_lang}")
                else:
                    print("    (no per-language data)")

                print("\n  Dimensions:")
                for dim_name, dim_data in dimensions.items():
                    level = dim_data.get("level", "")
                    score = dim_data.get("score", 0.0)
                    print(f"    - {dim_name}: level={level}, score={score:.2f}")

                display_langs = [
                    lang for lang in sorted(per_lang.keys())
                    if str(lang).lower() != "unknown"
                ]
                print("\n  Detected languages:")
                if display_langs:
                    for lang in display_langs:
                        print(f"    - {lang}")
                else:
                    print("    (no reliable languages detected)")

                print("\n  Detected skills (filtered by confidence):")
                if deduped_skill_names:
                    for s in deduped_skill_names:
                        print(f"    - {s}")
                else:
                    print("    (no high-confidence skills detected)")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Timeline: Projects & Skills (using stored analysis)
    # ------------------------------------------------------------------

    def display_project_timeline(self) -> None:
        """
        Print a chronological list of projects and the skills exercised
        in each, based on projects currently stored in the database.

        Also prints a per-skill first-use timeline, so you can see when
        each skill first appeared and in which project.
        """
        projects = list(self.project_manager.get_all())
        if not projects:
            print("\nNo projects found in the database. Run analyses first.")
            return

        rows = get_projects_with_skills_timeline_from_projects(projects)

        print("\n=== Project Timeline (Chronological) ===")
        if not rows:
            print("No projects with valid dates found.")
            return

        for when, name, skills in rows:
            skills_str = ", ".join(skills) if skills else "(no skills recorded)"
            print(f"{when.isoformat()} — {name}: {skills_str}")

        events = get_skill_timeline_from_projects(projects)
        if not events:
            return

        print("\n=== Skill First-Use Timeline ===")

        first_seen: Dict[str, Any] = {}
        for ev in events:
            key = ev.skill.lower()
            if key not in first_seen:
                first_seen[key] = ev

        ordered = sorted(
            first_seen.values(),
            key=lambda ev: (ev.when, ev.skill.lower()),
        )

        for ev in ordered:
            project_name = ev.project or "(unknown project)"
            print(f"{ev.when.isoformat()} — {ev.skill} (first seen in {project_name})")

    # ------------------------------------------------------------------
    # Badge analysis (stateless, no DB schema changes)
    # ------------------------------------------------------------------

    def analyze_badges(self) -> None:
        """
        Compute and display badges for the currently loaded project.

        Uses:
        - Metadata & category summary (ProjectMetadataExtractor)
        - Language share (analyze_language_share)
        - Skills (SkillAnalyzer)
        - Configured usernames (ConfigManager) for author_count / collaboration_status

        Badges + fun facts are printed; DB schema is not modified.
        """
        if not self.zip_path:
            print("No project loaded. Please load a zip file first.\n")
            return

        path_obj = Path(self.zip_path)
        if not path_obj.exists() or not zipfile.is_zipfile(path_obj):
            print(f"Error: {path_obj} is not a valid zip file.")
            return

        print("\n=== BADGE ANALYSIS ===")

        # 1) Metadata & category summary
        with self.suppress_output():
            meta_payload = self.metadata_extractor.extract_metadata() or {}
        project_meta = meta_payload.get("project_metadata") or {}
        category_summary = meta_payload.get("category_summary") or {}

        def _to_int(value, default: int = 0) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        def _to_float(value, default: float = 0.0) -> float:
            try:
                return float(value)
            except (TypeError, ValueError):
                return default

        total_files = _to_int(project_meta.get("total_files"))
        total_size_kb = _to_float(project_meta.get("total_size_kb"))
        total_size_mb = _to_float(project_meta.get("total_size_mb"))
        duration_days = _to_int(project_meta.get("duration_days"))

        # 2) Languages + skills from extracted repo
        languages: Dict[str, float] = {}
        skills: set[str] = set()

        temp_dir = extract_zip(str(path_obj))
        try:
            languages = analyze_language_share(temp_dir) or {}

            # Reuse SkillAnalyzer to infer skills
            skill_analyzer = SkillAnalyzer(Path(temp_dir))
            result = skill_analyzer.analyze()
            skill_items = result.get("skills", []) or []

            for item in skill_items:
                name = None
                if isinstance(item, dict):
                    name = item.get("skill") or item.get("name")
                else:
                    name = getattr(item, "skill", None) or getattr(item, "name", None)
                if name:
                    skills.add(str(name))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        # 3) Author / collaboration info from config
        usernames = self._config_manager.get("usernames") or []
        author_count = len(usernames) or 1
        collaboration_status = "individual" if author_count <= 1 else "collaborative"

        project_name = self.zip_path.stem

        snapshot = ProjectAnalyticsSnapshot(
            name=project_name,
            total_files=total_files,
            total_size_kb=total_size_kb,
            total_size_mb=total_size_mb,
            duration_days=duration_days,
            category_summary=category_summary,
            languages=languages,
            skills=skills,
            author_count=author_count,
            collaboration_status=collaboration_status,
        )

        badge_ids = assign_badges(snapshot)
        fun_facts = build_fun_facts(snapshot, badge_ids)

        project = self.project_manager.get_by_name(project_name)
        if project is not None:
            if not hasattr(project, "badges"):
                project.badges = []
            project.badges = badge_ids

        # 4) Print badges & fun facts
        if badge_ids:
            print("Badges:")
            for b in badge_ids:
                print(f"  - {b}")
        else:
            print("No badges assigned for this project.")

        if fun_facts:
            print("\nFun facts:")
            for fact in fun_facts:
                print(f"  • {fact}")

        print()

    # ------------------------------------------------------------------
    # Display stored analysis
    # ------------------------------------------------------------------

    def display_analysis_results(self, projects: Iterable[Project]) -> None:
        """Print previously stored analysis results."""
        projects_list = list(projects)
        if not projects_list:
            print("\nNo analysis results to display.")
            return

        print(f"\n{'=' * 30}")
        print("      Analysis Results")
        print(f"{'=' * 30}")

        for project in projects_list:
            project.display()

    # ------------------------------------------------------------------
    # Resume Insights (merged behaviour)
    # ------------------------------------------------------------------

    def generate_resume_insights(self) -> None:
        """
        Extract Git repos from the ZIP, then for each selected repo:
        - match it to the corresponding folder in the ZIP tree,
        - run ProjectMetadataExtractor,
        - compute language shares,
        - generate resume-friendly bullet points and summaries.
        """
        print("\nGenerating Resume Insights...\n")

        if not self.zip_path:
            print("No project loaded. Please load a zip file first.\n")
            return

        # Extract ZIP once per session and cache the directory
        if getattr(self, "cached_extract_dir", None) is None:
            self.cached_extract_dir = Path(extract_zip(self.zip_path))

        extract_dir = self.cached_extract_dir

        # use RepoProjectBuilder to fully build project objects
        builder = RepoProjectBuilder(self.root_folder)
        projects = builder.scan(extract_dir)
        if not projects:
            print("No Git repositories found.")
            return

        # Rebuild project list by matching against DB whenever possible
        all_projects: List[Project] = []

        for proj in projects:  # 'projects' is from builder.scan()
            project_from_db = self.project_manager.get_by_name(proj.name)
            if project_from_db:
                all_projects.append(project_from_db)
            else:
                all_projects.append(proj)  # fall back to scanned project

        # Sort by existing resume_score (DB values or default 0)
        projects = sorted(all_projects, key=lambda p: p.resume_score, reverse=True)

        # ---- Project selection loop ----
        while True:
            print("\nGit projects detected (ranked by resume score):")
            projects_list = list(projects)

            for i, proj in enumerate(projects_list, start=1):
                print(f" {i}. {proj.name} (Score: {proj.resume_score:.2f})")

            return_option = len(projects_list) + 1

            print("\nSelect an option:")
            print(" 0. Generate insights for ALL projects")
            if len(projects_list) >= 3:
                print(" 3. Generate for Top 3 Projects")
            print(f" {return_option}. Return to Main Menu")

            choice = input("Choose a project number: ").strip()

            # Return to main menu
            if choice == str(return_option):
                print("\nReturning to main menu...\n")

                # CLEAN UP TEMP EXTRACT DIR
                if hasattr(self, "cached_extract_dir") and self.cached_extract_dir:
                    try:
                        shutil.rmtree(self.cached_extract_dir, ignore_errors=True)
                    except Exception:
                        pass

                self.cached_extract_dir = None
                return

            # Generate for ALL
            if choice == "0":
                selected = projects_list
            elif choice == "3" and len(projects_list) >= 3:
                selected = projects_list[:3]
            else:
                try:
                    idx = int(choice) - 1
                    if idx < 0 or idx >= len(projects_list):
                        print("Invalid selection.\n")
                        continue
                    selected = [projects_list[idx]]
                except ValueError:
                    print("Invalid input.\n")
                    continue

            # ---- Process each selected repo ----
            for proj in selected:
                print("\n==============================")
                print(f" Resume Insights for: {proj.name}")
                print("==============================\n")

                # Determine correct folder in ZIP tree
                if len(projects_list) == 1:
                    folder = self.root_folder
                else:
                    folder = self._find_folder_by_name(self.root_folder, proj.name)

                if folder is None:
                    print(f"[ERROR] Could not locate folder for repo '{proj.name}' inside the ZIP.")
                    print("Skipping this project.\n")
                    continue

                # Metadata extraction (silenced)
                extractor = ProjectMetadataExtractor(folder)
                with self.suppress_output():
                    metadata_full = extractor.extract_metadata()

                metadata = metadata_full.get("project_metadata", {})
                categorized_files = metadata_full.get(
                    "category_summary",
                    {"counts": {}, "percentages": {}},
                )

                # File collection
                files = extractor.collect_all_files()

                # Language share (per directory)
                language_share = analyze_language_share(extract_dir / proj.name)

                # Language list (per-file detection)
                repo_languages = set()
                for f in files:
                    lang = detect_language_per_file(Path(f.file_name))
                    if lang:
                        repo_languages.add(lang)

                repo_languages = sorted(repo_languages)

                # Load or create DB record
                stored = self.project_manager.get_by_name(proj.name)
                if stored is None:
                    stored = Project(
                        name=proj.name,
                        file_path=str(extract_dir / proj.name),
                        root_folder=proj.name,
                    )

                # Store metadata
                stored.num_files = metadata.get("total_files", 0)
                stored.size_kb = metadata.get("total_size_kb", 0)

                # Dates
                try:
                    start = metadata.get("start_date")
                    end = metadata.get("end_date")

                    stored.date_created = datetime.fromisoformat(start) if start else None
                    stored.last_modified = datetime.fromisoformat(end) if end else None
                except Exception:
                    stored.date_created = None
                    stored.last_modified = None

                # Store categories + languages
                stored.categories = categorized_files.get("counts", {})
                stored.languages = repo_languages

                # Save the update
                self.project_manager.set(stored)

                # Generate insights
                resume_insights_generator = ResumeInsightsGenerator(
                    metadata=metadata,
                    categorized_files=categorized_files,
                    language_share=language_share,
                    language_list=repo_languages,
                    project=proj,
                )

                bullets = resume_insights_generator.generate_resume_bullet_points()
                summary = resume_insights_generator.generate_project_summary()

                # Print resume insights to console
                if hasattr(resume_insights_generator, "display_insights"):
                    resume_insights_generator.display_insights(bullets, summary)
                else:
                    print("Bullet points:")
                    for b in bullets:
                        print(f"  • {b}")
                    print("\nSummary:")
                    print(summary)

    def _cleanup_temp(self) -> None:
        """Delete the extracted ZIP temp folder if it exists."""
        if getattr(self, "cached_extract_dir", None):
            try:
                shutil.rmtree(self.cached_extract_dir, ignore_errors=True)
                print(f"[Cleanup] Removed temp folder: {self.cached_extract_dir}")
            except Exception as e:
                print(f"[Cleanup Error] {e}")
            self.cached_extract_dir = None

    def _signal_cleanup(self, signum, frame) -> None:
        """Handle Ctrl+C cleanly by cleaning temp folder then exiting."""
        print("\n[Interrupted] Cleaning up temporary files...")
        self._cleanup_temp()
        raise SystemExit(0)

    # ------------------------------------------------------------------
    # Folder helper
    # ------------------------------------------------------------------

    def _find_folder_by_name(self, folder, target_name):
        """Recursively search the ZIP-parsed tree (ProjectFolder structure) for a folder by name."""
        if folder.name == target_name:
            return folder

        for sub in folder.subdir:
            found = self._find_folder_by_name(sub, target_name)
            if found:
                return found

        return None

    # ------------------------------------------------------------------
    # New folder & main menu
    # ------------------------------------------------------------------

    def analyze_new_folder(self) -> None:
        """Reset caches and load a new ZIP project."""
        if getattr(self, "cached_extract_dir", None):
            self._cleanup_temp()

        print("\nLoading new project...")
        success = self.load_zip()

        if success:
            print("\nNew project loaded successfully\n")
        else:
            print("\nFailed to load new project.\n")

    def run_all(self) -> None:
        print("Running All Analyzers\n")
        self.initialize_projects()
        self.analyze_git_and_contributions()
        if self.root_folder:
            self.analyze_metadata()
            self.analyze_categories()
            self.print_tree()
            self.analyze_languages()
        self.analyze_skills()
        self.analyze_badges()
        print("\nAnalyses complete.\n")

    def retrieve_previous_insights(self, projects: Iterable[Project]) -> Dict[str, Tuple[List[str], str]]:
        """
        Retrieves previous insights for all stored projects.
        Returns as a dict with the project name as the key and the insights as the value.
        """
        projects_list = list(projects)
        results: Dict[str, Tuple[List[str], str]] = {}
        for project in projects_list:
            bullets = project.bullets or []
            summary = project.summary or ""
            results[project.name] = (bullets, summary)
        return results

    def print_previous_insights(self, insights_dict: Dict[str, Tuple[List[str], str]]) -> None:
        """
        Takes the dict returned by `retrieve_previous_insights` and displays them
        via ResumeInsightsGenerator.display_insights.
        """
        if not insights_dict:
            print("\nNo previous insights to display.")
            return
        for key, (bullets, summary) in insights_dict.items():
            print("\n==============================")
            print(f" Resume Insights for: {key}")
            print("==============================\n")
            ResumeInsightsGenerator.display_insights(bullets, summary)

    def delete_previous_insights(self, projects: Iterable[Project]) -> None:
        projects_list = list(projects)
        if not projects_list:
            print("\nNo previous insights to delete.")
            return
        for project in projects_list:
            project.bullets = []
            project.summary = ""
            self.project_manager.set(project)
        print("Project insights have been deleted.")
        return

    def run(self) -> None:
        """The main interactive loop for the Project Analyzer."""
        print("Welcome to the Project Analyzer.\n")
        signal.signal(signal.SIGINT, self._signal_cleanup)

        if not self.load_zip():
            return

        self.initialize_projects()

        while True:
            print("""
                ========================
                Project Analyzer
                ========================
                Choose an option:
                0. Initialize/Re-scan Projects (Recommended First Step)
                1. Analyze Git Repository & Contributions
                2. Extract Metadata & File Statistics
                3. Categorize Files by Type
                4. Print Project Folder Structure
                5. Analyze Languages Detected
                6. Run All Analyses
                7. Analyze New Folder
                8. Change Selected Users
                9. Analyze Skills (Calculates Resume Score)
                10. Generate Resume Insights
                11. Retrieve Previous Resume Insights
                12. Delete Previous Resume Insights
                13. Display Previous Results
                14. Show Project Timeline (Projects & Skills)
                15. Analyze Badges
                16. Exit
                  """)

            choice = input("Selection: ").strip()

            if choice in {"0", "1", "2", "3", "4", "5", "6", "8", "9", "10", "13"}:
                if not self.zip_path:
                    if not self.load_zip():
                        return
                    self.initialize_projects()

            if choice == "0":
                self.initialize_projects()
            elif choice == "1":
                self.analyze_git_and_contributions()
            elif choice == "2":
                self.analyze_metadata()
            elif choice == "3":
                self.analyze_categories()
            elif choice == "4":
                self.print_tree()
            elif choice == "5":
                self.analyze_languages()
            elif choice == "6":
                self.run_all()
            elif choice == "7":
                self.analyze_new_folder()
                if self.zip_path:
                    self.initialize_projects()
            elif choice == "8":
                self.change_selected_users()
            elif choice == "9":
                self.analyze_skills()
            elif choice == "10":
                self.generate_resume_insights()
            elif choice == "11":
                projects = self.project_manager.get_all()
                insights_dict = self.retrieve_previous_insights(projects)
                self.print_previous_insights(insights_dict)
            elif choice == "12":
                projects = self.project_manager.get_all()
                self.delete_previous_insights(projects)
            elif choice == "13":
                projects = self.project_manager.get_all()
                self.display_analysis_results(projects)
            elif choice == "14":
                self.display_project_timeline()
            elif choice == "15":
                self.analyze_badges()
            elif choice == "16":
                print("Exiting Project Analyzer.")
                # CLEAN UP TEMP DIR ON EXIT
                self._cleanup_temp()
                return
            else:
                print("Invalid input. Try again.\n")
