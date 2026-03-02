import signal, threading
from uuid import uuid4
import json, os, sys, re, shutil, contextlib, zipfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Dict, Any

from src.project_timeline import (
    get_projects_with_skills_timeline_from_projects,
    get_skill_timeline_from_projects,
)
from src.analyzers.badge_engine import (
    ProjectAnalyticsSnapshot,
    assign_badges,
    build_fun_facts,
)
from datetime import datetime

from src.ZipParser import parse_zip_to_project_folders, toString, extract_zip
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.FileCategorizer import FileCategorizer
from src.analyzers.language_detector import detect_language_per_file, analyze_language_share
from src.analyzers.contribution_analyzer import ContributionAnalyzer, ContributionStats
from utils.RepoFinder import RepoFinder
from src.managers.ProjectManager import ProjectManager
from src.managers.FileHashManager import FileHashManager
from src.models.Project import Project
from src.models.Report import Report
from src.models.ReportProject import ReportProject, PortfolioDetails
from src.ProjectFolder import ProjectFolder
from src.analyzers.SkillAnalyzer import SkillAnalyzer
from src.generators.ResumeInsightsGenerator import ResumeInsightsGenerator
from src.generators.PortfolioGenerator import PortfolioGenerator
from src.managers.ConfigManager import ConfigManager
from src.ProjectRanker import ProjectRanker
from src.analyzers.RepoProjectBuilder import RepoProjectBuilder
from utils.file_hashing import compute_file_hash
from src.exporters.ReportExporter import ReportExporter
from src.managers.ReportManager import ReportManager
from src.services.ReportEditor import ReportEditor
from src.services.InsightEditor import InsightEditor
from src.analyzers.role_inference_analyzer import RoleInferenceAnalyzer

MIN_DISPLAY_CONFIDENCE = 0.5  # only show skills with at least this confidence


class ProjectAnalyzer:
    """The main entry point of our program. Caller to all of our dedicated analysis-classes."""

    def __init__(self, config_manager: ConfigManager, root_folders: List[ProjectFolder], zip_path: Path):
        self.root_folders: List[ProjectFolder] = root_folders
        self.zip_path: Path = zip_path
        self._config_manager = config_manager

        self.file_categorizer = FileCategorizer()
        self.repo_finder = RepoFinder()
        self.project_manager = ProjectManager()
        self.file_hash_manager = FileHashManager()
        self.contribution_analyzer = ContributionAnalyzer()

        self.cached_extract_dir: Optional[Path] = None
        self.cached_projects: List[Project] = []
        self.import_batch_id: str = uuid4().hex

        self.report_manager = ReportManager()
        self.report_exporter = ReportExporter()
        
        self.role_inference_analyzer = RoleInferenceAnalyzer()

        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._signal_cleanup)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @contextlib.contextmanager
    def suppress_output(self):
        """Temporarily suppress stdout and stderr."""
        with open(os.devnull, "w") as devnull:
            old_stdout, old_stderr, sys.stdout, sys.stderr = sys.stdout, sys.stderr, devnull, devnull
            try:
                yield
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr

    @staticmethod
    def clean_path(raw_input: str) -> Path:
        """Cleans and validates a user-provided file path."""
        stripped = raw_input.strip().strip("'").strip('"')
        if os.name == "nt":
            return Path(os.path.expanduser(stripped))
        return Path(os.path.expanduser(re.sub(r'\\(.)', r'\1', stripped)))

    def _get_projects(self) -> List[Project]:
        """Ensures cached_projects is populated, fetching from DB if needed."""
        if not self.cached_projects:
            self.cached_projects = list(self.project_manager.get_all())
        return self.cached_projects

    def _get_zip_project_summary(self, project_name: str) -> Optional[Dict[str, Any]]:
        root_folder = self._find_folder_by_name_recursive(project_name)
        if not root_folder:
            return None
        extractor = ProjectMetadataExtractor(root_folder)
        files = extractor.collect_all_files()
        return extractor.compute_time_and_size_summary(files)
    
    def _has_project_changed(self, project: Project) -> bool:
        """Returns True if any file in the project has a new/unseen hash."""
        project_root = Path(project.file_path)
        if not project_root.exists():
            return False
        for root, _, files in os.walk(project_root):
            for name in files:
                file_path = Path(root) / name
                file_hash = compute_file_hash(file_path)
                if not file_hash:
                    continue
                if not self.file_hash_manager.has_hash(file_hash):
                    return True  # found a new/changed file
        return False

    def _register_project_files(self, project: Project) -> Dict[str, int]:
        project_root = Path(project.file_path)
        if not project_root.exists():
            return {"new": 0, "duplicate": 0}

        new_count = 0
        duplicate_count = 0
        for root, _, files in os.walk(project_root):
            for name in files:
                file_path = Path(root) / name
                file_hash = compute_file_hash(file_path)
                if not file_hash:
                    continue
                if self.file_hash_manager.register_hash(
                    file_hash, str(file_path), project.name
                ):
                    new_count += 1
                else:
                    duplicate_count += 1
        return {"new": new_count, "duplicate": duplicate_count}


    def _ensure_scores_are_calculated(self) -> List[Project]:
        """
        Checks for projects with a zero score, runs skill analysis on them silently,
        and returns a complete list of all projects with their updated scores.
        """
        all_projects = self._get_projects()
        projects_needing_score = [p for p in all_projects if p.resume_score == 0]

        if projects_needing_score:
            self.analyze_skills(projects=projects_needing_score, silent=True)
            self.cached_projects = []
            all_projects = self._get_projects()

        return all_projects

    def _select_project(self, prompt: str) -> Optional[Project]:
        """
        A generic helper to display a numbered list of projects and have the user select one.
        Returns the selected Project object or None.
        """
        projects = self._get_projects()
        if not projects:
            print("\nNo projects found to select from.")
            return None

        print(f"\n{prompt}")
        for i, proj in enumerate(projects, 1):
            print(f"  {i}: {proj.name}")

        try:
            choice_str = input(f"Enter your choice (1-{len(projects)}), or 'q' to cancel: ").strip().lower()
            if choice_str == 'q':
                return None
            choice = int(choice_str)
            if 1 <= choice <= len(projects):
                return projects[choice - 1]
            else:
                print("Invalid selection.")
                return None
        except ValueError:
            print("Invalid input. Please enter a number.")
            return None

    # ------------------------------------------------------------------
    # ZIP Loading and Project Initialization
    # ------------------------------------------------------------------

    @staticmethod
    def load_zip() -> Tuple[List[ProjectFolder], Path]:
        """Prompts user for ZIP file and parses into a list of root folder trees."""
        zip_path = ProjectAnalyzer.clean_path(input("Please enter the path to the zipped folder: "))
        while not (os.path.exists(zip_path) and zipfile.is_zipfile(zip_path)):
            zip_path = ProjectAnalyzer.clean_path(input("Invalid path or not a zipped file. Please try again: "))
        print("Parsing ZIP structure...")
        root_folders = parse_zip_to_project_folders(zip_path)
        if not root_folders:
            print("Warning: No projects could be parsed from the zip file.")
        else:
            print(f"Project(s) parsed successfully: {[f.name for f in root_folders]}\n")
        return root_folders, zip_path

    def ensure_cached_dir(self) -> Path:
        """Extracts the ZIP to a temp directory if not already done."""
        if self.cached_extract_dir is None:
            self.cached_extract_dir = Path(extract_zip(str(self.zip_path)))
        return self.cached_extract_dir

    def initialize_projects(self) -> List[Project]:
        print("\n--- Initializing Project Records ---")
        if not self.zip_path or not self.root_folders:
            print("No project loaded. Please load a zip file first.\n")
            return []
        temp_dir = self.ensure_cached_dir()
        repo_builder = RepoProjectBuilder(self.root_folders)
        created_projects: List[Project] = []
        projects_from_builder = repo_builder.scan(temp_dir)
        if not projects_from_builder:
            print("No projects found to build.")
            return []
        print(f"Found {len(projects_from_builder)} project(s). Saving initial records...")
        for proj_new in projects_from_builder:
            if summary := self._get_zip_project_summary(proj_new.name):
                if summary.get("total_files") is not None:
                    proj_new.num_files = int(summary["total_files"])
                if summary.get("total_size_kb") is not None:
                    proj_new.size_kb = int(summary["total_size_kb"])
                if summary.get("start_date"):
                    proj_new.date_created = datetime.strptime(summary["start_date"], "%Y-%m-%d")
                if summary.get("end_date"):
                    proj_new.last_modified = datetime.strptime(summary["end_date"], "%Y-%m-%d")

            proj_existing = self.project_manager.get_by_name(proj_new.name)
            proj_new.import_batch_id = self.import_batch_id

            if proj_existing:
                proj_existing.import_batch_id = self.import_batch_id
                if self._has_project_changed(proj_new):
                    proj_existing.file_path, proj_existing.root_folder = proj_new.file_path, proj_new.root_folder
                    if proj_new.num_files:
                        proj_existing.num_files = proj_new.num_files
                    if proj_new.size_kb:
                        proj_existing.size_kb = proj_new.size_kb
                    if proj_new.date_created and not proj_existing.date_created:
                        proj_existing.date_created = proj_new.date_created
                    if proj_new.last_modified:
                        proj_existing.last_modified = proj_new.last_modified
                    proj_existing.last_accessed = datetime.now()
                    self.project_manager.set(proj_existing)
                    self._register_project_files(proj_existing)
                    print(f"  - Updated existing project: {proj_existing.name}")
                else:
                    proj_existing.last_accessed = datetime.now()
                    self.project_manager.set(proj_existing)
                    print(f"  - No changes detected, refreshed batch for: {proj_existing.name}")
                created_projects.append(proj_existing)
            else:
                proj_new.last_accessed = datetime.now()
                proj_new.import_batch_id = self.import_batch_id
                self.project_manager.set(proj_new)
                self._register_project_files(proj_new)
                print(f"  - Created new project record: {proj_new.name} with ID {proj_new.id}")
                created_projects.append(proj_new)
        self.cached_projects = created_projects
        return created_projects
    # ------------------------------------------------------------------
    # Analysis Methods
    # ------------------------------------------------------------------

    def _prompt_for_usernames(self, author_map: Dict[str, str]) -> Optional[List[str]]:
        """
        author_map: {email: display_name}
        Returns list of selected emails (canonical identities).
        """
        print("\nPlease select your username(s) from the list of project contributors:")
        if not author_map:
            print("No authors found in the commit history.")
            return None

        entries = sorted(author_map.items(), key=lambda x: x[1].lower())  # sort by display name
        for i, (email, name) in enumerate(entries):
            print(f"  {i + 1}: {name} <{email}>")

        print("\nYou can select multiple authors by entering numbers separated by commas (e.g., 1, 3).")
        try:
            choice_str = input("Enter your choice(s) (or 'q' to quit): ").strip()
            if choice_str.lower() == "q":
                return None
            selected_emails = []
            for choice in [c.strip() for c in choice_str.split(",")]:
                index = int(choice) - 1
                if not (0 <= index < len(entries)):
                    print(f"Invalid number '{choice}'. Please try again.")
                    return self._prompt_for_usernames(author_map)
                selected_emails.append(entries[index][0])  # append email
            return sorted(list(set(selected_emails)))
        except (ValueError, IndexError):
            print("Invalid input format. Please enter numbers separated by commas.")
            return self._prompt_for_usernames(author_map)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
            return None

    def _get_or_select_usernames(self, authors: List[str]) -> Optional[List[str]]:
        usernames = self._config_manager.get("usernames")
        if usernames and isinstance(usernames, list):
            print(f"\nAnalyzing contributions for current users: {', '.join(usernames)}")
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

    def _aggregate_stats(self, author_stats: Dict[str, ContributionStats], selected_authors: Optional[List[str]] = None) -> ContributionStats:
        aggregated = ContributionStats()
        authors_to_aggregate = selected_authors if selected_authors is not None else author_stats.keys()
        for author in authors_to_aggregate:
            if stats := author_stats.get(author):
                aggregated.lines_added += stats.lines_added
                aggregated.lines_deleted += stats.lines_deleted
                aggregated.total_commits += stats.total_commits
                aggregated.files_touched.update(stats.files_touched)
                for category, count in stats.contribution_by_type.items():
                    aggregated.contribution_by_type[category] += count
        return aggregated

    @staticmethod
    def _resolve_selected_authors(requested_authors: List[str], available_authors: List[str]) -> List[str]:
        """Match requested usernames to available author names, case-insensitively."""
        available_map = {name.casefold(): name for name in available_authors}
        resolved = []

        for requested in requested_authors:
            match = available_map.get((requested or "").casefold())
            if match and match not in resolved:
                resolved.append(match)

        return sorted(resolved)

    def change_selected_users(self) -> None:
        """Allows the user to change their configured username selection."""
        print("\n--- Change Selected Users ---")
        projects = self._get_projects()
        if not projects:
            return

        all_author_map: Dict[str, str] = {}
        for project in projects:
            if (Path(project.file_path) / ".git").exists():
                with self.suppress_output():
                    project_author_map = self.contribution_analyzer.get_all_authors(str(project.file_path), config_manager=self._config_manager)
                all_author_map.update(project_author_map)

        if not all_author_map:
            print("No Git authors found in any project.")
            return

        new_usernames = self._prompt_for_usernames(all_author_map)
        if new_usernames:
            self._config_manager.set("usernames", new_usernames)
            print(f"\nSuccessfully updated selected users to: {', '.join(new_usernames)}")
        else:
            print("\nNo changes made to user selection.")

    def _pretty_role(self, role_key: str) -> str:
        if not role_key or role_key in ("role_none", "none"):
            return "None"

        role_key = role_key.replace("role_", "")

        mapping = {
            "devops": "DevOps",
            "qa": "QA",
            "backend": "Backend",
            "frontend": "Frontend",
            "docs": "Documentation",
        }

        return mapping.get(role_key, role_key.capitalize())
    def analyze_git_and_contributions(self, projects: Optional[List[Project]] = None, interactive: bool = True) -> None:
      """
      Analyze contributions for each project:
      - Use get_all_authors() to set total author_count reliably
      - Optionally prompt for selected usernames if not configured
      - Compute detailed stats where possible
      """
      print("\n--- Git Repository & Contribution Analysis ---")
      target_projects = projects or self._get_projects()
      if not target_projects:
          return

      for project in target_projects:
          repo_path = Path(project.file_path)
          if not (repo_path / ".git").exists():
              continue

          print(f"\n--- Analyzing contributions for: {project.name} ---")

          with self.suppress_output():
              author_map = self.contribution_analyzer.get_all_authors(str(repo_path), config_manager=self._config_manager)

          # Detect duplicates and optionally write .mailmap
          author_map = self.contribution_analyzer.detect_and_write_mailmap(str(repo_path), author_map, config_manager=self._config_manager)

          project.author_count = len(author_map)
          project.collaboration_status = "Collaborative" if project.author_count > 1 else "Individual"

          if interactive:
              selected_emails = self._get_or_select_usernames(author_map) or []
          else:
              configured_usernames = self._config_manager.get("usernames")
              if isinstance(configured_usernames, list) and configured_usernames:
                  selected_emails = configured_usernames
              else:
                  selected_emails = list(author_map.keys())

          with self.suppress_output():
              all_author_stats = self.contribution_analyzer.analyze(str(repo_path))

          project.authors = sorted([author_map[e] for e in selected_emails if e in author_map])
          project.contributor_roles = {}

          if all_author_stats:
              roles_obj = self.role_inference_analyzer.analyze(all_author_stats)
              project.contributor_roles = {
                  user: {
                      "primary_role": r.primary_role.value,
                      "confidence": float(r.confidence),
                      "secondary_roles": [sr.value for sr in (r.secondary_roles or [])],
                      "evidence": r.evidence or {},
                  }
                  for user, r in roles_obj.items()
              }

          if all_author_stats:
              selected_stats = self._aggregate_stats(all_author_stats, selected_emails)
              total_stats = self._aggregate_stats(all_author_stats)
              project.author_contributions = [stats.to_dict() for stats in all_author_stats.values()]
              project.individual_contributions = self.contribution_analyzer.calculate_share(selected_stats, total_stats)
          else:
              print("  - No detailed contribution stats available; using author list for collaboration status.")

          project.last_accessed = datetime.now()
          self.project_manager.set(project)
          print(f"  - Total Contributors: {project.author_count}")
          print(f"  - Collaboration Status: {project.collaboration_status}")
          if project.contributor_roles:
              print(" - Inferred Roles:")
              for user, info in project.contributor_roles.items():
                  pretty = self._pretty_role(info.get("primary_role", "none"))
                  confidence_pct = int(float(info.get("confidence", 0.0)) * 100)
                  print(f"    - {user} → User Role: {pretty} ({confidence_pct}%)")

          print(f"  - Saved data for '{project.name}'.")

    def analyze_metadata(self, projects: Optional[List[Project]] = None) -> None:
        """Extracts and saves metadata for all projects or a specific list of them."""
        print("\n--- Metadata & File Statistics ---")
        for project in (projects or self._get_projects()):
            print(f"\nAnalyzing metadata for: {project.name}")
            root_folder = self._find_folder_by_name_recursive(project.name)
            if not root_folder:
                print(f"  - Skipping: could not find matching folder in ZIP.")
                continue

            with self.suppress_output():
                extractor = ProjectMetadataExtractor(root_folder)
                metadata_full = extractor.extract_metadata(repo_path=project.file_path) or {}

            project_meta = metadata_full.get("project_metadata", {})
            if num_files := project_meta.get("total_files"):
                project.num_files = int(num_files)
            if size_kb := project_meta.get("total_size_kb"):
                project.size_kb = int(size_kb)
            if start_date := project_meta.get("start_date"):
                project.date_created = datetime.strptime(start_date, "%Y-%m-%d")
            if end_date := project_meta.get("end_date"):
                project.last_modified = datetime.strptime(end_date, "%Y-%m-%d")

            project.last_accessed = datetime.now()
            self.project_manager.set(project)
            print(f"  - Saved metadata for '{project.name}'.")

    def analyze_categories(self, projects: Optional[List[Project]] = None) -> None:
        """Analyzes and saves file categories. Can run on all projects or a specific list."""
        print("\n--- File Categories Analysis ---")
        for project in (projects or self._get_projects()):
            print(f"\nAnalyzing categories for: {project.name}")
            root_folder = self._find_folder_by_name_recursive(project.name)
            if not root_folder:
                print(f"  - Skipping: could not find matching folder in ZIP.")
                continue

            files = ProjectMetadataExtractor(root_folder).collect_all_files()
            file_dicts = [{"path": f.full_path, "language": getattr(f, "language", "Unknown")} for f in files]

            metrics = self.file_categorizer.compute_metrics(file_dicts)
            project.categories = metrics.get("counts", {})

            self.project_manager.set(project)
            print(json.dumps(project.categories, indent=2))

    def analyze_languages(self, projects: Optional[List[Project]] = None) -> None:
        """Detects language share. Can run on all projects or a specific list."""
        print("\n--- Language Detection ---")
        for project in (projects or self._get_projects()):
            print(f"\nProject: {project.name}")
            project_root = Path(project.file_path)
            if not project_root.exists():
                print(f"  - Skipping: Path not found.")
                continue

            language_share = analyze_language_share(project_root)
            project.languages = list(language_share.keys())
            project.language_share = language_share
            self.project_manager.set(project)

            if not language_share:
                print("  - No languages detected.")
                continue
            for lang, share in language_share.items():
                print(f"  - {lang}: {share:.1f}%")

    def analyze_skills(self, projects: Optional[List[Project]] = None, silent: bool = False) -> None:
        """Runs skill analysis and calculates resume score for projects."""
        if not silent:
            print("\n--- Enriching Projects with Skill Analysis & Scoring ---")

        projects_to_run = projects if projects is not None else self._get_projects()

        for project in projects_to_run:
            if not silent:
                print(f"\nAnalyzing skills for: {project.name}...")

            with self.suppress_output():
                if not Path(project.file_path).exists():
                    if not silent:
                        print(f"  - Warning: Path not found. Skipping.")
                    continue

                result = SkillAnalyzer(Path(project.file_path)).analyze()

                skills_raw = result.get("skills", [])
                filtered_skills = []
                for item in skills_raw:
                    name, conf = (item.get("skill"), item.get("confidence")) if isinstance(item, dict) else (getattr(item, 'skill', None), getattr(item, 'confidence', 0.0))
                    if name and conf >= MIN_DISPLAY_CONFIDENCE:
                        filtered_skills.append(name.strip())
                project.skills_used = sorted(list(set(filtered_skills)))
                project.skills_selected = project.skills_used #Select all skills by default.

                if dimensions := result.get("dimensions", {}):
                    if td := dimensions.get("testing_discipline"):
                        project.testing_discipline_score, project.testing_discipline_level = td.get("score", 0.0), td.get("level", "")
                    if doc := dimensions.get("documentation_habits"):
                        project.documentation_habits_score, project.documentation_habits_level = doc.get("score", 0.0), doc.get("level", "")

                if overall := result.get("stats", {}).get("overall"):
                    project.total_loc = overall.get("total_lines_of_code", 0)
                    project.comment_ratio = overall.get("comment_ratio", 0.0)
                    project.test_file_ratio = overall.get("test_file_ratio", 0.0)

                ranker = ProjectRanker(project)
                ranker.calculate_resume_score()

                self.project_manager.set(project)

            if not silent:
                print(f"  - Successfully enriched '{project.name}'. Resume Score: {project.resume_score:.2f}")

    def analyze_badges(self) -> None:
        """
        Compute and display badges for a selected project.
        """
        print("\n--- Badge Analysis ---")
        project = self._select_project("Select a project to analyze for badges:")
        if not project:
            return

        if not all([project.num_files, project.date_created, project.last_modified, project.categories, project.languages, project.skills_used]):
            print(f"\n  - Prerequisite data missing for {project.name}. Running required analyses...")
            self.analyze_metadata(projects=[project])
            self.analyze_categories(projects=[project])
            self.analyze_languages(projects=[project])
            self.analyze_skills(projects=[project], silent=True)
            print(f"  - Prerequisite analyses complete for {project.name}.")
            project = self.project_manager.get_by_name(project.name)

        duration_days = (project.last_modified - project.date_created).days if project.last_modified and project.date_created else 0

        snapshot = ProjectAnalyticsSnapshot(
            name=project.name,
            total_files=project.num_files,
            total_size_kb=project.size_kb,
            total_size_mb=(project.size_kb / 1024),
            duration_days=duration_days,
            category_summary={"counts": project.categories},
            languages=project.language_share,
            skills=set(project.skills_used),
            author_count=project.author_count,
            collaboration_status=project.collaboration_status,
        )

        badge_ids = assign_badges(snapshot)
        fun_facts = build_fun_facts(snapshot, badge_ids)

        if badge_ids:
            print("\nBadges Earned:")
            for b in badge_ids:
                print(f"  - {b}")
        else:
            print("No badges assigned for this project.")

        if fun_facts:
            print("\nFun Facts:")
            for fact in fun_facts:
                print(f"  • {fact}")
        print()

    # ------------------------------------------------------------------
    # Display and Utility Methods
    # ------------------------------------------------------------------

    def _generate_insights_for_project(self, project: Project):
        """Helper function to run the insight generation for a single project."""
        print(f"\n--- Generating Resume Insights for: {project.name} ---")

        with self.suppress_output():
            root_folder = self._find_folder_by_name_recursive(project.name)
            if not root_folder:
                print(f"Could not find project '{project.name}' in ZIP structure.")
                return
            metadata = (ProjectMetadataExtractor(root_folder).extract_metadata(repo_path=project.file_path) or {}).get("project_metadata", {})

        try:
            repo_path = Path(project.file_path)
            if (repo_path / ".git").exists():
                with self.suppress_output():
                    repo_authors = self.contribution_analyzer.get_all_authors(str(repo_path))
                if repo_authors:
                    project.author_count = len(repo_authors)
                    project.collaboration_status = "collaborative" if project.author_count > 1 else "individual"
                    self.project_manager.set(project)
        except Exception:
            pass

        gen = ResumeInsightsGenerator(
            metadata, project.categories, project.language_share, project, project.languages
        )

        project.bullets = gen.generate_resume_bullet_points()
        project.summary = gen.generate_project_summary()
        project.portfolio_entry = gen.generate_portfolio_entry()

        portfolio_gen = PortfolioGenerator(
            metadata, project.categories, project.language_share, project, project.languages
        )
        project.portfolio_details = portfolio_gen.generate_portfolio_details()

        print("\nGenerated Portfolio Entry:\n")
        print(project.portfolio_entry)

        project.portfolio_entry = self.edit_portfolio_entry_cli(project.portfolio_entry)

        self.project_manager.set(project)
        print(f"\nGenerated and saved insights for {project.name}:")
        gen.display_insights(project.bullets, project.summary, project.portfolio_entry)

    def generate_insights_noninteractive(self, projects):
        """
        API-safe version of insights generation:
        - generates bullets/summary/portfolio entry/details
        - does NOT call any CLI editor
        """
        for project in projects:
            self._generate_insights_for_project_noninteractive(project)


    def _generate_insights_for_project_noninteractive(self, project: Project):
        # Ensure prerequisite analyses exist (like CLI)
        if not project.categories or not project.num_files or not project.languages:
            self.analyze_metadata(projects=[project])
            self.analyze_categories(projects=[project])
            self.analyze_languages(projects=[project])
            project = self.project_manager.get_by_name(project.name)

        # Ensure contribution info if possible
        if not project.author_count or project.author_count <= 1:
            self.analyze_git_and_contributions(projects=[project], interactive=False)
            project = self.project_manager.get_by_name(project.name)
        """Generate resume + portfolio insights for a single project (non-interactive)."""
        # Find the root folder for metadata extraction
        with self.suppress_output():
            with self.suppress_output():
                root_folder = self._find_folder_by_name_recursive(project.name)

                # always try the repo path itself
                if not root_folder:
                    root_folder = project.file_path

                extracted = ProjectMetadataExtractor(root_folder).extract_metadata(
                    repo_path=project.file_path
                ) or {}
                metadata = (extracted.get("project_metadata", {}) or {})

            extracted = ProjectMetadataExtractor(root_folder).extract_metadata(
                repo_path=project.file_path
            ) or {}
            metadata = (extracted.get("project_metadata", {}) or {})

        # Update collaboration info if repo has .git
        try:
            repo_path = Path(project.file_path)
            if (repo_path / ".git").exists():
                with self.suppress_output():
                    repo_authors = self.contribution_analyzer.get_all_authors(str(repo_path))
                if repo_authors:
                    project.author_count = len(repo_authors)
                    project.collaboration_status = (
                        "collaborative" if project.author_count > 1 else "individual"
                    )
        except Exception:
            pass

        # Generate resume insights
        gen = ResumeInsightsGenerator(
            metadata, project.categories, project.language_share, project, project.languages
        )
        project.bullets = gen.generate_resume_bullet_points()
        project.summary = gen.generate_project_summary()
        project.portfolio_entry = gen.generate_portfolio_entry()

        # Generate portfolio details
        portfolio_gen = PortfolioGenerator(
            metadata, project.categories, project.language_share, project, project.languages
        )
        project.portfolio_details = portfolio_gen.generate_portfolio_details()

        # Persist
        self.project_manager.set(project)

    def generate_resume_insights(self) -> None:
        """Presents a menu to generate resume insights, ensuring scores are calculated first."""
        sorted_projects = self.get_projects_sorted_by_score()

        while True:
            print("\n--- Generate Resume Insights ---")
            print("\nPlease select a project, or choose a special option:")
            for i, proj in enumerate(sorted_projects, 1):
                print(f"  {i}: {proj.name} (Score: {proj.resume_score:.2f})")

            num_projects = len(sorted_projects)
            top_3_option = num_projects + 1
            all_option = num_projects + 2
            exit_option = num_projects + 3

            print("\n--- Special Options ---")
            print(f"  {top_3_option}: Generate for Top 3 Projects")
            print(f"  {all_option}: Generate for ALL scored projects")
            print(f"  {exit_option}: Return to Main Menu")

            choice_str = input("Your choice: ").strip()

            try:
                choice = int(choice_str)
                selected_projects = []

                if choice == top_3_option:
                    selected_projects = sorted_projects[:3]
                elif choice == all_option:
                    selected_projects = sorted_projects
                elif choice == exit_option:
                    print("Returning to main menu...")
                    return
                elif 1 <= choice <= num_projects:
                    selected_projects = [sorted_projects[choice - 1]]
                else:
                    print("Invalid selection. Please try again.")
                    continue

                for proj in selected_projects:
                    if not proj.categories or not proj.num_files or not proj.languages:
                         print(f"\n  - Prerequisite data missing for {proj.name}. Running required analyses...")
                         self.analyze_metadata(projects=[proj])
                         self.analyze_categories(projects=[proj])
                         self.analyze_languages(projects=[proj])
                         print(f"  - Prerequisite analyses complete for {proj.name}.")

                    if not proj.author_count or proj.author_count <= 1:
                        print(f"\n  - Author data missing or incomplete for {proj.name}. Running contribution analysis...")
                        orig_cached = self.cached_projects
                        self.cached_projects = [proj]
                        self.analyze_git_and_contributions()
                        self.cached_projects = orig_cached
                        proj = self.project_manager.get_by_name(proj.name)
                        print(f"  - Contribution analysis complete for {proj.name} (Authors: {proj.author_count}).")

                    self._generate_insights_for_project(proj)

                self.cached_projects = []
                return

            except ValueError:
                print("Invalid input. Please enter a number.")
                continue

    def edit_portfolio_entry_cli(self, entry: str) -> str:
        parts = InsightEditor.parse_portfolio_entry(entry)

        while True:
            print("\nEdit Menu:")
            print("1) Role/Timeline line")
            print("2) Technologies line")
            print("3) Project Overview")
            print("4) Achievements")
            print("5) Done")
            choice = input("> ").strip()

            if choice == "1":
                print(f"\nCurrent:\n{parts.role_line}")
                new_val = input("New (Enter to keep): ").rstrip()
                if new_val:
                    if "**Role:**" not in new_val or "**Timeline:**" not in new_val:
                        print("\nPlease keep the format like:")
                        print("**Role:** <something> | **Timeline:** <something>")
                        print("Example: **Role:** Team Contributor (Team of 7) | **Timeline:** 25 days")
                    else:
                        parts.role_line = new_val

            elif choice == "2":
                print(f"\nCurrent:\n{parts.tech_line}")
                new_val = input("New (Enter to keep): ").rstrip()
                if new_val:
                    parts.tech_line = new_val

            elif choice == "3":
                print(f"\nCurrent:\n{parts.overview}")
                new_val = input("New (Enter to keep): ").rstrip()
                if new_val:
                    parts.overview = new_val

            elif choice == "4":
                print("\nCurrent achievements:")
                for i, a in enumerate(parts.achievements, 1):
                    print(f"  {i}. {a}")
                print("Type a number to edit, 'a' to add, 'd' to delete, or Enter to go back.")
                sub = input("> ").strip().lower()

                if sub.isdigit():
                    idx = int(sub) - 1
                    if 0 <= idx < len(parts.achievements):
                        print(f"Current: {parts.achievements[idx]}")
                        new_a = input("New (Enter to keep): ").rstrip()
                        if new_a:
                            parts.achievements[idx] = new_a

                elif sub == "a":
                    new_a = input("Add achievement: ").rstrip()
                    if new_a:
                        parts.achievements.append(new_a)

                elif sub == "d":
                    n = input("Delete which number?: ").strip()
                    if n.isdigit():
                        idx = int(n) - 1
                        if 0 <= idx < len(parts.achievements):
                            parts.achievements.pop(idx)

            elif choice == "5":
                break
            else:
                print("Invalid choice.")

        return InsightEditor.build_portfolio_entry(parts)

    def retrieve_previous_insights(self) -> None:
        print("\n--- Previous Resume Insights ---")
        for project in self._get_projects():
            if project.bullets or project.summary or project.portfolio_entry:
                print(f"\n{'='*20}\nInsights for: {project.name}\n{'='*20}")
                ResumeInsightsGenerator.display_insights(
                    project.bullets, project.summary, project.portfolio_entry
                )
    
    def update_score_and_date(self) -> None:
        
        items = self._get_projects()
        sorted_items = sorted(items, key=lambda project: project.resume_score, reverse=True)

        refresh = self.helper_score_and_date(False, sorted_items)

        while refresh != -1:
            refresh = sorted(refresh, key=lambda project: project.resume_score, reverse=True)

            refresh = self.helper_score_and_date(True, refresh)

    def helper_score_and_date(self, refresh:bool, sorted_items:list): #returns list if refreshing, -1 if exiting
        '''Ability to modify scores and dates of projects while displaying a list of all projects ordered by score'''

        hr = (f"{'':{'─'}>{83}}")   #horizontal rule
        RED = '\033[91m'
        GREEN = '\033[92m'
        GREY = '\033[97m'
        ENDC = '\033[0m'

        COMMANDS = (
            '[COMMANDS]\n'+
            '| Alter Score |'+
            GREY+"  '[IDX]"+ENDC+' score '+GREY+"[VALUE]'"+ENDC+'                                         |\n'+
            '| Alter Date  |'+
            GREY+"  '[IDX]"+ENDC+' created '+GREY+"[YYYY-MM-DD]'"+ENDC+' / '+GREY+"'[IDX]"+ENDC+' modified '+GREY+"[YYYY-MM-DD]'"+ENDC+'  |\n'+
            '\n'+
            "|  Save  |  's'  |\n"+
            "|  Exit  |  'x'  |\n"+hr+'\n'
            )
        idx=0

        #print list of projects
        print("Projects by resume score:")
        print(hr)
        for project in sorted_items:
            print(
                f'[{(idx+1):02d}] | 'f'score: [{(project.resume_score):05.2f}] | 'f'{project.name:<10.10} | 'f'created: [{str(project.date_created):<10.10}] | 'f'modified: [{str(project.last_modified):<10.10}]'
            )
            idx+=1
        print(hr)

        #print commands
        print(COMMANDS)

        #loop for project selection:
        valid = False

        #Displays success message on refresh
        if refresh:
            prompt = GREEN+"Changes successful, don't forget to save!. Input Command:"+ENDC
        else:
            prompt = 'Please input command:'
        
        while not valid:
            print(prompt)
            choice = input()

            if choice == 'x':
                return -1
            
            elif choice == 's':
                for project in sorted_items:
                    try:
                        self.project_manager.set(project)
                    except:
                        print('Error in project manager SET method')
                prompt = GREEN+"Changes Saved. Input Command:"+ENDC

            else:
                words = choice.strip().lower().split(' ')
                if len(words) == 3:
                    if words[0].isdigit():
                        if int(words[0])>=1 and int(words[0])<=len(sorted_items):
                            if words[1]=='score':
                                try:
                                    newscore = float(words[2])
                                    idx = int(words[0])-1
                                    sorted_items[int(idx)].resume_score = newscore

                                    return sorted_items

                                except ValueError:
                                    prompt = RED+"'"+words[2]+"' is not a valid score. Please try again:"+ENDC

                            elif words[1]=='created':
                                try:
                                    newdate = datetime.strptime(words[2],'%Y-%m-%d').date()
                                    idx = int(words[0])-1
                                    sorted_items[int(idx)].date_created = newdate

                                    return sorted_items

                                except ValueError:
                                    prompt = RED+"'"+words[2]+"' is not a valid date. Please try again:"+ENDC

                            elif words[1]=='modified':
                                try:
                                    newdate = datetime.strptime(words[2],'%Y-%m-%d').date()
                                    idx = int(words[0])-1
                                    sorted_items[int(idx)].last_modified = newdate

                                    return sorted_items
                                
                                except ValueError:
                                    prompt = RED+"'"+words[2]+"' is not a valid date. Please try again:"+ENDC
                            else:
                                prompt = RED+"'"+words[1]+"' is not a valid command. Please try again:"+ENDC
                        else:
                            prompt = RED+'Index provided is not in range. Please try again:'+ENDC
                    else:
                        prompt = RED+'Index provided is not in range. Please try again:'+ENDC
                else:
                    prompt = RED+'Incorrect command format. Please try again:'+ENDC
            #clear last two lines
            sys.stdout.write("\033[1A"+f"{'':{' '}>{100}}\n"+"\033[2A"+f"{'':{' '}>{100}}\n"+"\033[1A")

    def retrieve_full_portfolio(self) -> None:
        """
        Aggregates all previously generated portfolio entries into a single,
        professional portfolio display. Skips projects without generated entries.
        """
        print("\n" + "="*50)
        print("          PROFESSIONAL PORTFOLIO          ")
        print("="*50 + "\n")

        projects = self._get_projects()
        portfolio_projects = [p for p in projects if p.portfolio_entry]

        if not portfolio_projects:
            print("No portfolio entries found. Please generate insights for projects first.")
            return

        portfolio_projects.sort(key=lambda x: x.last_modified or datetime.min, reverse=True)

        for i, project in enumerate(portfolio_projects, 1):
            print(project.portfolio_entry)
            print("-" * 50 + "\n")

        print(f"Total Projects in Portfolio: {len(portfolio_projects)}\n")
        edit = input("Would you like to edit one of these entries? (y/n): ").strip().lower()
        if edit != "y":
            return

        print("\nSelect a project to edit:")
        for i, p in enumerate(portfolio_projects, 1):
            print(f"  {i}: {p.name}")

        choice = input(f"Enter your choice (1-{len(portfolio_projects)}), or 'q' to cancel: ").strip().lower()
        if choice == "q":
            return

        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(portfolio_projects)):
                print("Invalid selection.")
                return
        except ValueError:
            print("Invalid input.")
            return

        project = portfolio_projects[idx]

        project.portfolio_entry = self.edit_portfolio_entry_cli(project.portfolio_entry)

        self.project_manager.set(project)
        self.cached_projects = []  # refresh cache each time
        print("\nSaved updated portfolio entry.\n")

    def delete_previous_insights(self) -> None:
        """Deletes the stored resume insights for a user-selected project."""
        project = self._select_project("Select a project to delete insights from:")
        if not project:
            return
        project.bullets, project.summary, project.portfolio_entry = [], "", ""
        project.portfolio_details = PortfolioDetails()
        self.project_manager.set(project)
        print(f"Successfully deleted insights for {project.name}.")

    def display_project_timeline(self) -> None:
        print("\n--- Project & Skill Timeline ---")
        projects = self._get_projects()
        if not projects:
            return
        rows = get_projects_with_skills_timeline_from_projects(projects)
        print("\n=== Project Timeline (Chronological) ===")
        if not rows:
            print("No projects with valid dates found.")
        for when, name, skills in rows:
            print(f"{when.isoformat()} — {name}: {', '.join(skills) if skills else '(no skills)'}")
        events = get_skill_timeline_from_projects(projects)
        if not events:
            return
        print("\n=== Skill First-Use Timeline ===")
        first_seen = {ev.skill.lower(): ev for ev in reversed(events)}
        for ev in sorted(first_seen.values(), key=lambda e: (e.when, e.skill.lower())):
            print(f"{ev.when.isoformat()} — {ev.skill} (first seen in {ev.project or 'unknown'})")

    def display_analysis_results(self) -> None:
        print(f"\n{'=' * 30}\n      Analysis Results\n{'=' * 30}")
        self.display_ranked_projects()

    def get_projects_sorted_by_score(self) -> List[Project]:
        """Return all projects with ensured resume scores, sorted descending, excluding zero-score projects."""
        projects = self._ensure_scores_are_calculated()
        scored = [p for p in projects if p.resume_score > 0]
        return sorted(scored, key=lambda p: p.resume_score, reverse=True)

    def display_ranked_projects(self,sorted_projects=None) -> None:
        """Display all scored projects sorted by resume score."""
        if sorted_projects is None:
            sorted_projects = self.get_projects_sorted_by_score()
        if not sorted_projects:
            print("\nNo projects with calculated scores to display.")
            return

        for project in sorted_projects:
            project.display()

    def print_tree(self) -> None:
        print("\n--- Project Folder Structures ---")
        if not self.root_folders:
            print("No project structure loaded.")
        for root in self.root_folders:
            print(toString(root))

    def create_report(self):
        """Allow the user to select projects and create a report object."""
        sorted_projects = self.get_projects_sorted_by_score()

        if not sorted_projects:
            print("\nNo scored projects available to include in a report.")
            return

        print("\n--- Create Report ---")
        print("\nPlease select which projects you'd like included in the report.")

        selected_projects = self._select_multiple_projects(sorted_projects)
        if selected_projects is None:
            print("\nReturning to main menu.")
            return

        if not self._validate_resume_insights(selected_projects):
            return

        print("\nEnter a title for your report (or press Enter for default):")
        title = input("Title: ").strip()
        if not title:
            title = "My Project Report"

        print("\nSelect sorting method for the report:")
        print("  1: Resume Score (default)")
        print("  2: Date Created")
        print("  3: Last Modified")
        print("  q: Cancel")

        sort_choice = input("Your choice: ").strip().lower()
        if sort_choice == "q":
            print("\nCancelled. Returning to main menu.")
            return

        sort_map = {
            "1": "resume_score",
            "2": "date_created",
            "3": "last_modified",
        }
        sort_by = sort_map.get(sort_choice, "resume_score")

        report_projects = [ReportProject.from_project(p) for p in selected_projects]

        report = Report(
            id=None,
            title=title,
            date_created=datetime.now(),
            sort_by=sort_by,
            projects=report_projects,
            notes=None
        )

        print("\nReport created successfully:")
        print(f"  Title: {report.title}")
        print(f"  Sort By: {report.sort_by}")
        print(f"  Included Projects: {[p.project_name for p in report_projects]}\n")

        self.report_manager.create_report(report)


    def delete_report(self) -> None:
        """Deletes a user-selected report and all its associated projects."""
        reports_summary = self.report_manager.list_reports_summary()
        print("\n--- Delete Report ---")
        if not reports_summary:
            print("\nYou don't have any stored reports!")
            return

        print(f"{'ID':<5} {'Title':<35} {'Created':<20} {'Projects':<10}")
        print("-" * 75)

        valid_ids = []
        for rs in reports_summary:
            valid_ids.append(rs["id"])
            date_str = datetime.fromisoformat(rs["date_created"]).strftime("%Y-%m-%d %H:%M")
            print(f"{rs['id']:<5} {rs['title']:<35} {date_str:<20} {rs['project_count']:<10}")

        print("-" * 75)

        while True:
            choice = input("\nEnter Report ID to delete (or 'q' to cancel): \n").strip().lower()
            if choice == "q":
                print("Cancelled.")
                return
            if not choice.isdigit():
                print("Please enter a valid number or 'q' to cancel.")
                continue

            report_id = int(choice)
            if report_id not in valid_ids:
                print(f"Invalid ID. Please choose from: {', '.join(map(str, valid_ids))}")
                continue
            break

        # Load the report so we can show a confirmation prompt
        report = self.report_manager.get_report(report_id)
        if not report:
            print(f"Error loading report {report_id}.")
            return

        print(f"\nYou are about to delete: '{report.title}' ({len(report.projects)} project(s))\n")
        confirm = input("Are you sure? This cannot be undone. (y/n): ").strip().lower()

        if confirm != "y":
            print("Deletion cancelled.")
            return

        success = self.report_manager.delete_report(report_id)
        if success:
            print(f"\nReport '{report.title}' has been deleted.")
        else:
            print(f"\nFailed to delete report {report_id}. It may have already been removed.")
        
    def _select_single_project(self, sorted_projects: List[Project]) -> Optional[Project]:
        print("\nPlease enter the id of the project you'd like to select.\n")
        print("Enter 'q' to cancel.\n")

        for i, proj in enumerate(sorted_projects, 1):
            print(f"  {i}: {proj.name} (Score: {proj.resume_score:.2f})")

        choice_str = input("\nYour selection: ").strip().lower()

        if choice_str == "q":
            return None

        try:
            idx = int(choice_str)
            if 1 <= idx <= len(sorted_projects):
                return sorted_projects[idx - 1]
            else:
                print(f"Invalid project number: {idx}. Please enter a number between 1 and {len(sorted_projects)}.")
                return self._select_single_project(sorted_projects)
        except ValueError:
            print("Invalid input. Please enter a single number.")
            return self._select_single_project(sorted_projects)


    def _select_multiple_projects(self, sorted_projects: List[Project]) -> Optional[List[Project]]:
        print("\nSelect one or more projects by entering numbers separated by commas.\n")
        print("Enter 'q' to cancel.\n")

        for i, proj in enumerate(sorted_projects, 1):
            print(f"  {i}: {proj.name} (Score: {proj.resume_score:.2f})")

        choice_str = input("\nYour selection: ").strip().lower()
        if choice_str == "q":
            return None

        try:
            indices = [int(x.strip()) for x in choice_str.split(",")]
            selected = []
            for idx in indices:
                if 1 <= idx <= len(sorted_projects):
                    selected.append(sorted_projects[idx - 1])
                else:
                    print(f"Invalid project number: {idx}")
                    return self._select_multiple_projects(sorted_projects)
            return selected
        except ValueError:
            print("Invalid input. Please enter numbers separated by commas.")
            return self._select_multiple_projects(sorted_projects)

    def _select_report_for_export(self) -> Optional[Report]:
        reports_summary = self.report_manager.list_reports_summary()

        if not reports_summary:
            print("\n❌ No reports found. Create a report first before exporting.")
            return None

        print("\n" + "="*90)
        print("Available Reports")
        print("="*90)
        print(f"{'ID':<5} {'Title':<35} {'Created':<20} {'Projects':<10} {'Avg Score':<10}")
        print("-"*90)

        for report_summary in reports_summary:
            date_created = datetime.fromisoformat(report_summary['date_created'])
            date_str = date_created.strftime('%Y-%m-%d %H:%M')

            report = self.report_manager.get_report(report_summary['id'])
            avg_score = f"{report.average_score:.1f}" if report else "N/A"

            print(f"{report_summary['id']:<5} {report_summary['title']:<35} {date_str:<20} "
                f"{report_summary['project_count']:<10} {avg_score:<10}")

        print("-"*90)

        while True:
            try:
                choice = input("\nEnter Report ID to export (or 'q' to cancel): ").strip()

                if choice.lower() == 'q':
                    print("Export cancelled.")
                    return None

                report_id = int(choice)

                valid_ids = [r['id'] for r in reports_summary]
                if report_id not in valid_ids:
                    print(f"❌ Invalid ID. Please choose from: {', '.join(map(str, valid_ids))}")
                    continue

                break

            except ValueError:
                print("❌ Please enter a valid number or 'q' to cancel.")

        report = self.report_manager.get_report(report_id)
        if not report:
            print(f"❌ Error loading report {report_id}")
            return None
        return report
    
    def _validate_resume_insights(self, projects: List[Project]) -> bool:
        """Return True if all projects have resume insights; otherwise print errors and return False."""
        missing = []

        for p in projects:
            if not p.bullets or not isinstance(p.bullets, list):
                missing.append((p.name, "bullets"))
            if not p.summary:
                missing.append((p.name, "summary"))
            if not p.portfolio_entry:
                missing.append((p.name, "portfolio_entry"))
            if not p.portfolio_details:
                missing.append((p.name, "portfolio_details"))

        if not missing:
            return True

        print("\n❌ Cannot create report. Some projects are missing resume insights:")
        for proj, field in missing:
            print(f"  - {proj}: missing {field}")

        print("\nPlease run 'Generate Resume Insights' (Option 10) before creating a report.")
        return False


    def trigger_resume_generation(self) -> Optional[Path]:
        """
        Interactive prompt to generate a resume from a report.
        Displays all available reports and lets user select one.

        Returns:
            Path to generated PDF, or None if cancelled/failed
        """
        report = self._select_report_for_export()
        if not report:
            return None

        print(f"\n{'='*60}")
        print(f"📋 Selected Report: {report.title}")
        print(f"{'='*60}")
        print(f"Created: {report.date_created.strftime('%Y-%m-%d %H:%M')}")
        print(f"Projects: {len(report.projects)}")
        print(f"Average Score: {report.average_score:.1f}")

        if report.notes:
            print(f"Notes: {report.notes}")

        print(f"\n{'Projects included:':}")
        for i, proj in enumerate(report.projects, 1):
            tech_stack = []
            if proj.languages:
                tech_stack.extend(proj.languages[:2])
            if proj.frameworks:
                tech_stack.extend(proj.frameworks[:2])

            tech_str = ", ".join(tech_stack) if tech_stack else "No tech stack"
            print(f"  {i}. {proj.project_name} ({tech_str}) - Score: {proj.resume_score:.1f}")

        print(f"{'='*60}\n")

        default_filename = f"{report.title.replace(' ', '_').lower()}_resume.pdf"
        filename_input = input(f"Output filename (default: '{default_filename}'): ").strip()

        filename = filename_input if filename_input else default_filename

        if not filename.endswith('.pdf'):
            filename += '.pdf'

        confirm = input(f"\n✓ Generate resume as '{filename}'? (y/n): ").strip().lower()

        if confirm != 'y':
            print("Resume generation cancelled.")
            return None

        print("\n⏳ Generating resume...")

        try:
            pdf_path = self._generate_resume(report, filename)
            print(f"\n✅ Resume successfully generated!")
            print(f"📄 Saved to: {pdf_path}")
            return pdf_path

        except ValueError as e:
            print(f"\n❌ Validation Error: {e}")
            print("💡 Tip: Make sure you've set your name, email, and phone in config.")
            return None

        except RuntimeError as e:
            print(f"\n❌ Generation Error: {e}")
            return None

        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            return None

    def trigger_portfolio_generation(self) -> Optional[Path]:
        report = self._select_report_for_export()
        if not report:
            return None
        if not report.projects:
            print("Error: Report contains no projects.")
            return None

        missing = [p.project_name for p in report.projects if not p.portfolio_details or not p.portfolio_details.project_name]
        if missing:
            print(f"\n❌ Cannot generate portfolio. Missing portfolio details for: {', '.join(missing)}")
            print("Please run 'Generate Resume Insights' (Option 10) first.")
            return None

        default_filename = f"{report.title.replace(' ', '_').lower()}_portfolio.pdf"
        filename_input = input(f"Output filename (default: '{default_filename}'): ").strip()
        filename = filename_input if filename_input else default_filename
        if not filename.endswith('.pdf'):
            filename += '.pdf'

        confirm = input(f"\n✓ Generate portfolio as '{filename}'? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Portfolio generation cancelled.")
            return None

        print("\n⏳ Generating portfolio...")
        try:
            pdf_path = self._generate_portfolio(report, filename)
            print(f"\n✅ Portfolio successfully generated!")
            print(f"📄 Saved to: {pdf_path}")
            return pdf_path
        except ValueError as e:
            print(f"\n❌ Validation Error: {e}")
            return None
        except RuntimeError as e:
            print(f"\n❌ Generation Error: {e}")
            return None
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
            return None

    def _generate_resume(self, report, output_filename: str = "resume.pdf") -> Path:
        """
        Generate a PDF resume from a report object.

        Args:
            report: Report object to export
            output_filename: Name of the PDF file to generate (default: "resume.pdf")

        Returns:
            Path to the generated PDF file

        Raises:
            ValueError: If report not found or config incomplete
            RuntimeError: If LaTeX not installed or PDF generation fails
        """
        if not report.projects:
            raise ValueError("Cannot generate resume: report has no projects")

        required_fields = ["name", "email", "phone"]
        missing_fields = [
            field for field in required_fields
            if not self._config_manager.get(field)
        ]

        if missing_fields:
            raise ValueError(
                f"Cannot generate resume: missing required config fields: {', '.join(missing_fields)}\n"
                f"Please set these using the config command."
            )

        output_path = Path(output_filename)
        if not output_path.is_absolute():
            output_path = Path("resumes") / output_filename

        exporter = ReportExporter()
        try:
            exporter.export_to_pdf(
                report=report,
                config_manager=self._config_manager,
                output_path=output_filename,
                template="jake"
            )
        except RuntimeError as e:
            raise RuntimeError(f"Failed to generate PDF: {e}")

        return Path("resumes") / output_filename

    def _generate_portfolio(self, report, output_filename: str = "portfolio.pdf") -> Path:
        if not report.projects:
            raise ValueError("Cannot generate portfolio: report has no projects")
        output_path = Path("portfolios") / output_filename
        exporter = ReportExporter()
        exporter.export_to_pdf(
            report=report,
            config_manager=self._config_manager,
            output_path=str(output_path),
            template="portfolio"
        )
        return output_path



    def trigger_report_editing(self) -> None:
        """
        Interactive prompt to edit an existing report (and config fields) without exporting.
        Persists updates back to the reports database.
        """
        reports_summary = self.report_manager.list_reports_summary()
        if not reports_summary:
            print("\n❌ No reports found. Create a report first.")
            return

        print("\n" + "=" * 90)
        print("Available Reports")
        print("=" * 90)
        print(f"{'ID':<5} {'Title':<35} {'Created':<20} {'Projects':<10}")
        print("-" * 90)

        valid_ids = []
        for rs in reports_summary:
            valid_ids.append(rs["id"])
            date_created = datetime.fromisoformat(rs["date_created"])
            date_str = date_created.strftime("%Y-%m-%d %H:%M")
            print(f"{rs['id']:<5} {rs['title']:<35} {date_str:<20} {rs['project_count']:<10}")

        print("-" * 90)

        while True:
            choice = input("\nEnter Report ID to edit (or 'q' to cancel): ").strip().lower()
            if choice == "q":
                print("Edit cancelled.")
                return
            if not choice.isdigit():
                print("Please enter a valid number or 'q' to cancel.")
                continue

            report_id = int(choice)
            if report_id not in valid_ids:
                print(f"Invalid ID. Please choose from: {', '.join(map(str, valid_ids))}")
                continue
            break

        report = self.report_manager.get_report(report_id)
        if not report:
            print(f"Error loading report {report_id}")
            return

        editor = ReportEditor()
        edited = editor.edit_report_cli(report, self._config_manager)
        if not edited:
            print("No changes saved.")
            return

        self.report_manager.update_report(report)
        print("Report updated and saved.")


    def _default_updated_filename(self, filename: str) -> str:
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        base = filename[:-4]
        return f"{base}_updated.pdf"

    def _cleanup_temp(self):
        if self.cached_extract_dir:
            shutil.rmtree(self.cached_extract_dir, ignore_errors=True)

    def _signal_cleanup(self, s, f):
        print("\n[Interrupted] Cleaning up...")
        self._cleanup_temp()
        sys.exit(0)

    def _find_folder_by_name_recursive(self, target_name: str) -> Optional[ProjectFolder]:
        """
        Recursively searches the entire parsed ZIP tree for a folder by name,
        case-insensitively.
        """
        target_lower = target_name.lower()

        def search(folder: ProjectFolder) -> Optional[ProjectFolder]:
            if folder.name.lower() == target_lower:
                return folder
            for subfolder in folder.subdir:
                if found := search(subfolder):
                    return found
            return None

        for root in self.root_folders:
            if found := search(root):
                return found

        return None

    def analyze_new_folder(self) -> None:
        self._cleanup_temp()
        print("\nPreparing to load a new project...")
        root_folders, zip_path = ProjectAnalyzer.load_zip()
        if not root_folders:
            print("\nFailed to load new project.\n")
            self.root_folders, self.zip_path, self.cached_projects = [], None, []
            return
        self.root_folders, self.zip_path = root_folders, zip_path
        print("\nNew project loaded successfully\n")
        self.initialize_projects()

    def select_thumbnail(self) -> None:
        sorted_projects = self.get_projects_sorted_by_score()
        if not sorted_projects:
            print("\nNo scored projects available to include in a report.")
            return

        print("\n--- Select Thumbnail for a Given Project  ---")
        print("\nPlease select which project you'd like to add a thumbnail to.")
        project = self._select_single_project(sorted_projects)

        if project is None:
            print("\nReturning to main menu.")
            return

        print("\nEnter the filepath for the image: ")
        raw_path = input("Path: ")

        if not raw_path.strip():
            print("\nNo path provided. Returning to main menu.")
            return

        image_path = self.clean_path(raw_path)

        if not image_path.exists():
            print(f"\nError: File not found at '{image_path}'")
            return

        if not image_path.is_file():
            print(f"\nError: Path is not a file: '{image_path}'")
            return

        valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.ico', '.svg'}
        file_ext = image_path.suffix.lower()
        if file_ext not in valid_extensions:
            print(f"\nError: Invalid image format '{file_ext}'")
            print(f"Supported formats: {', '.join(sorted(valid_extensions))}")
            return

        thumbnails_dir = Path("thumbnails")
        thumbnails_dir.mkdir(exist_ok=True)

        thumbnail_filename = f"project_{project.id}_thumb{file_ext}"
        thumbnail_path = thumbnails_dir / thumbnail_filename

        try:
            shutil.copy(image_path, thumbnail_path)
            project.thumbnail = str(thumbnail_path)
            self.project_manager.set(project)
            print(f"\n✓ Thumbnail successfully added to '{project.name}'")
            print(f"  Saved to: {thumbnail_path}")
        except PermissionError:
            print(f"\nError: Permission denied when copying file")
        except Exception as e:
            print(f"\nError copying file: {e}")

    def run_all(self) -> None:
        print("\n--- Running All Supported Analyses ---")
        if not self._get_projects():
            print("Initializing projects first...")
            self.initialize_projects()

        if not self.cached_projects:
            print("Initialization failed. No projects to analyze.")
            return

        self.analyze_git_and_contributions()
        self.analyze_metadata()
        self.analyze_categories()
        self.analyze_languages()
        self.analyze_skills()
        self.display_project_timeline()
        print("\nAll analyses complete.\n")

    def menu_print_metadata_summary(self):
        """
        Display metadata that has already been analyzed and stored. This method is only used for Option 2 in our menu (Extract metadata & file statistics) to print it...
        """
        projects = self._get_projects()
        if not projects:
            print("No projects available.")
            return

        print("\n===== Project Metadata Summary =====")
        for project in projects:
            if not project.num_files:
                print(f"\n{project.name}: No metadata analyzed yet.")
                continue

            summary = {
                "total_files": project.num_files,
                "total_size_kb": project.size_kb,
                "start_date": project.date_created.strftime("%Y-%m-%d") if project.date_created else None,
                "end_date": project.last_modified.strftime("%Y-%m-%d") if project.last_modified else None,
            }

            print(f"\n--- {project.name} ---")
            print(json.dumps(summary, indent=2))

            if project.categories:
                print("\nFile category counts:")
                print(json.dumps(project.categories, indent=2))
            else:
                print("\nFile categories not analyzed yet.")

    def configure_personal_info(self) -> None:
        """Interactive prompt to store personal info used for resume generation."""
        print("\n===== Resume Personal Information =====")

        def prompt_value(label: str, key: str) -> None:
            current = self._config_manager.get(key, "")
            prompt = f"{label} [{current}]: " if current else f"{label}: "
            value = input(prompt).strip()
            if value == "":
                return
            if value == "-":
                self._config_manager.set(key, "")
                return
            self._config_manager.set(key, value)

        def prompt_yes_no(prompt: str) -> bool:
            while True:
                choice = input(prompt).strip().lower()
                if choice in {"y", "yes"}:
                    return True
                if choice in {"n", "no"}:
                    return False
                print("Please enter y or n.")

        prompt_value("Full name", "name")
        prompt_value("Email", "email")
        prompt_value("Phone", "phone")
        prompt_value("GitHub username", "github")
        prompt_value("LinkedIn handle", "linkedin")

        if prompt_yes_no("Update education history? (y/n): "):
            education_entries = []
            while True:
                add_entry = prompt_yes_no("Add an education entry? (y/n): ")
                if not add_entry:
                    break
                school = input("  School: ").strip()
                location = input("  Location: ").strip()
                degree = input("  Degree: ").strip()
                dates = input("  Dates (e.g., 2019 - 2023): ").strip()
                if not any([school, location, degree, dates]):
                    print("  Skipping empty entry.")
                    continue
                education_entries.append(
                    {
                        "school": school,
                        "location": location,
                        "degree": degree,
                        "dates": dates,
                    }
                )
            self._config_manager.set("education", education_entries)

        if prompt_yes_no("Update experience history? (y/n): "):
            experience_entries = []
            while True:
                add_entry = prompt_yes_no("Add an experience entry? (y/n): ")
                if not add_entry:
                    break
                title = input("  Title: ").strip()
                company = input("  Company: ").strip()
                location = input("  Location: ").strip()
                dates = input("  Dates (e.g., Jun 2022 - Present): ").strip()
                bullets_raw = input("  Bullets (separate with ;): ").strip()
                bullets = [b.strip() for b in bullets_raw.split(";") if b.strip()]
                if not any([title, company, location, dates, bullets]):
                    print("  Skipping empty entry.")
                    continue
                experience_entries.append(
                    {
                        "title": title,
                        "company": company,
                        "location": location,
                        "dates": dates,
                        "bullets": bullets,
                    }
                )
            self._config_manager.set("experience", experience_entries)

        print("Resume personal information saved.\n")
    
    def compare_projects(self):
        '''Compares projects by sorting the list of all projects based on different variables stored in Project objects'''
        projects = self._get_projects()
        pro_amt = len(projects)
        exiting = False

        b = ' │ '
        h = '#'

        print('''
┌─────────────────────────────────────────┐
│Please select which attribute to sort by:│
└─────────────────────────────────────────┘
    Stats:
        [1]  Size of project (kb)
        [2]  # of files
        [3]  # of Authors
        [4]  # of languages
        [5]  # of frameworks
        [6]  # of skills
        [7]  # of dependencies
        [8]  # of lines of code
    
    Ratios:
        [9]  Comments/lines of codex
        [10] Test file/code file
        [11] Average functions/code file

    Scores:
        [12] Testing Discipline Score
        [13] Documentation Habits Score
        [14] Modularity Score
        [15] Language Depth Score
        [16] Resume Score
    
    Chronology:
        [17] Date Created
        [18] Last Modified

        [x] Exit
    
Projects:
┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄''')

        width = 0
        for p in projects:
            width = max(width, len(p.name))

        for i,p in enumerate(projects):
            print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' + b)

        print("┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄")
        print("Your Selection (You may need to scroll up to see the list of sorting methods):")

        while (not exiting):
            choice = input()
            if choice in ['1','2','3','4','5','6','7','8','9','10','11','12','13','14','15','16','17','18']:
                #clear everything
                for _ in range((3+pro_amt)):
                    sys.stdout.write('\033[1A') # terminal cursor up one line
                    sys.stdout.write('\033[2K') # terminal clear current line

                #sort and print list of projects
                projects = self.sort_projects(projects, choice, width)

                print("┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄")
                print("Successfully sorted using method "+choice+". Your Selection:")
            
            elif choice == 'flush': #return projects list for testing purposes
                return projects
            
            elif choice == 'x': #exit this menu
                return -1
            
            else:
                # clear input and print error message before asking for new input
                sys.stdout.write('\033[1A') # terminal cursor up one line
                sys.stdout.write('\033[2K') # terminal clear current line
                sys.stdout.write('\033[1A') # terminal cursor up one line
                sys.stdout.write('\033[2K') # terminal clear current line
                print('Command does not exist. Please try again:')

    def sort_projects(self, projects: List[Project], sort_by:str, width:str):
        '''Sorts projects based on input from user. Intended to be ran from compare_projects()'''

        b = ' │ '
        h = '#'

        match sort_by:
            case '1':
                sorted_items = sorted(projects, key=lambda project: project.size_kb, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(p.size_kb)))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[Size (kb)]: ' + f'{str(p.size_kb)[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '2':
                sorted_items = sorted(projects, key=lambda project: project.num_files, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(p.num_files)))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[# of Files]: ' + f'{str(p.num_files)[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '3':
                sorted_items = sorted(projects, key=lambda project: project.author_count, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(p.author_count)))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[# of Authors]: ' + f'{str(p.author_count)[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '4':
                sorted_items = sorted(projects, key=lambda project: len(project.languages), reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(len(p.languages))))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[# of Languages]: ' + f'{str(len(p.languages))[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '5':
                sorted_items = sorted(projects, key=lambda project: len(project.frameworks), reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(len(p.frameworks))))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[# of Frameworks]: ' + f'{str(len(p.frameworks))[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '6':
                sorted_items = sorted(projects, key=lambda project: len(project.skills_used), reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(len(p.skills_used))))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[# of Skills Used]: ' + f'{str(len(p.skills_used))[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '7':
                sorted_items = sorted(projects, key=lambda project: len(project.dependencies_list), reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(len(p.dependencies_list))))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[# of Dependencies]: ' + f'{str(len(p.dependencies_list))[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '8':
                sorted_items = sorted(projects, key=lambda project: project.total_loc, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(p.total_loc)))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[# of Lines of Code]: ' + f'{str(p.total_loc)[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '9':
                sorted_items = sorted(projects, key=lambda project: project.comment_ratio, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(p.comment_ratio)))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[Comments per Lines of Code]: ' + f'{str(p.comment_ratio)[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '10':
                sorted_items = sorted(projects, key=lambda project: project.test_file_ratio, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(p.test_file_ratio)))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[Test files per Code Files]: ' + f'{str(p.test_file_ratio)[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '11':
                sorted_items = sorted(projects, key=lambda project: project.avg_functions_per_file, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(p.avg_functions_per_file)))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[Average Functions per Code File]: ' + f'{str(p.avg_functions_per_file)[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '12':
                sorted_items = sorted(projects, key=lambda project: project.testing_discipline_score, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(p.testing_discipline_score)))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[Testing Discipline Score]: ' + f'{str(p.testing_discipline_score)[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items          

            case '13':
                sorted_items = sorted(projects, key=lambda project: project.documentation_habits_score, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(p.documentation_habits_score)))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[Documentation Habits Score]: ' + f'{str(p.documentation_habits_score)[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '14':
                sorted_items = sorted(projects, key=lambda project: project.modularity_score, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(p.modularity_score)))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[Modularity Score]: ' + f'{str(p.modularity_score)[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '15':
                sorted_items = sorted(projects, key=lambda project: project.language_depth_score, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(p.language_depth_score)))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[Language Depth Score]: ' + f'{str(p.language_depth_score)[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items  

            case '16':
                sorted_items = sorted(projects, key=lambda project: project.resume_score, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(f'{p.resume_score:.2f}'))
                for i, p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[Resume Score]: ' + f'{p.resume_score:.2f}' +b)
                    
                return sorted_items

            case '17':
                sorted_items = sorted(projects, key=lambda project: project.date_created, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(p.date_created)))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[Date Created]: ' + f'{str(p.date_created)[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

            case '18':
                sorted_items = sorted(projects, key=lambda project: project.last_modified, reverse=True)

                sorted_width = 0
                for p in sorted_items:
                    sorted_width = max(sorted_width, len(str(p.last_modified)))

                for i,p in enumerate(sorted_items):
                    print(h+str(i+1) +b+ '[Name]: ' + f'{p.name[:width]:<{width}}' +b+ '[Last Modified]: ' + f'{str(p.last_modified)[:sorted_width]:<{sorted_width}}' +b)

                return sorted_items

    def edit_skills(self):
        '''Ability to toggle which elements in a project's list of skills are used'''
        hr = (f"{'':{'─'}>{83}}")   #horizontal rule
        RED = '\033[91m'
        GREEN = '\033[92m'
        GREY = '\033[97m'
        ENDC = '\033[0m'

        projects = self._get_projects()
        pro_amt = len(projects)

        saved = False
        staying = True

        print(hr+'\n[#] Select Project\n'+hr+'\n[x] Exit'+hr+'\nProjects:')
        for i,p in enumerate(projects):
            print ('['+str(i+1)+'] - ' + p.name)
        print(hr+'\nYour Selection:')

        while staying:
            selection = input()
            selection = selection.strip()

            if selection.lower() == 'x':
                return -1

            else:
                try:
                    if int(selection)>0 and int(selection)<=pro_amt:
                        proj = projects[(int(selection)-1)]

                        # if skills used is currently empty, fill it with all skills
                        if len(proj.skills_selected)==0:
                            for s in proj.skills_used:
                                proj.skills_selected.append(s)

                        skill_amt = len(proj.skills_used)

                        msg = "Your Selection:"
                        while staying:
                            if len(proj.skills_used)==0:
                                print('no skills in project')
                                return False
                            print(hr+'\n[#] Toggle Skill\n[a] Enable All\n'+hr+'\n[s] Save\n[x] Exit')
                            print(hr+'\n['+proj.name+"]'s Skills:\n"+hr)

                            for i,s in enumerate(proj.skills_used):
                                if s in proj.skills_selected:
                                    print (GREEN+'✓ ['+str(i+1)+'] - ' + s +ENDC)
                                elif s not in proj.skills_selected:
                                    print (RED+'✗ ['+str(i+1)+'] - ' + s +ENDC)
                                else:
                                    print (RED+'✗ ['+str(i+1)+'] - ' + s +ENDC)
                            
                            print(hr+'\n'+msg)

                            selection = input()
                            selection = selection.strip()

                            if selection == 'x':
                                return saved
                            
                            elif selection == 's':
                                try:
                                    self.project_manager.set(proj)
                                except:
                                    print('Error updating the database')
                                saved = True
                                msg = GREEN + 'Changes Saved Successfully. Your Selection:' + ENDC
                            
                            elif selection == 'a':
                                for s in proj.skills_used:
                                    proj.skills_selected.append(s)
                                msg = "All Skills Enabled. Your Selection:"
                                saved = False
                            else:
                                try:
                                    if (int(selection)-1)>=0 and (int(selection)-1)<skill_amt:
                                        skill = proj.skills_used[(int(selection)-1)]
                                        #remove if present, add if not
                                        #.remove() throws ValueError when skill not found.
                                        try:
                                            proj.skills_selected.remove(skill)
                                        except ValueError:
                                            proj.skills_selected.append(skill)
                                        msg = "Skill Toggled. Don't Forget To Save! Your Selection:"
                                        saved=False
                                    else:
                                        msg = RED+'Invalid Skill Index. Please try again:'+ENDC
                                except ValueError:
                                    msg = RED+'Invalid Skill Selection. Please try again:'+ENDC
                    else:
                        #clear input
                        sys.stdout.write('\033[1A') # terminal cursor up one line
                        sys.stdout.write('\033[2K') # terminal clear current line
                        #clear prompt message
                        sys.stdout.write('\033[1A') # terminal cursor up one line
                        sys.stdout.write('\033[2K') # terminal clear current line
                        #write error message
                        sys.stdout.write(RED+'Invalid Project Index. Please try again:'+ENDC+'\n')

                except ValueError:
                    #clear input
                    sys.stdout.write('\033[1A') # terminal cursor up one line
                    sys.stdout.write('\033[2K') # terminal clear current line
                    #clear prompt message
                    sys.stdout.write('\033[1A') # terminal cursor up one line
                    sys.stdout.write('\033[2K') # terminal clear current line
                    #write error message
                    sys.stdout.write(RED+'Invalid Project Selection. Please try again:'+ENDC+'\n')

    def run(self) -> None:
        """The main interactive menu loop."""
        print("\nWelcome to the Project Analyzer.\n")
        signal.signal(signal.SIGINT, self._signal_cleanup)
        while True:
            print("""
                ========================
                Project Analyzer
                ========================
                Choose an option:
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
                16. Retrieve Full Portfolio (Aggregated)
                17. Exit
                18. Enter Resume Personal Information
                19. Create Report (For Use With Resume Generation)
                20. Generate Resume (Export From Report as pdf)
                21. Generate Portfolio (Export From Report as pdf)
                22. Edit Report
                23. Delete Report
                24. Select Thumbnail for a Given Project
                98. Compare projects
                99. Edit project information (Scores & Dates)
                100. Toggle skills to showcase
                  """)

            choice = input("Selection: ").strip()

            if not self.zip_path and choice not in ["7", "17"]:
                print("No project loaded. Please analyze a new folder first.")
                continue

            menu = {
                "1": self.analyze_git_and_contributions, "2": self.menu_print_metadata_summary,
                "3": self.analyze_categories, "4": self.print_tree,
                "5": self.analyze_languages, "6": self.run_all,
                "7": self.analyze_new_folder, "8": self.change_selected_users,
                "9": self.analyze_skills, "10": self.generate_resume_insights,
                "11": self.retrieve_previous_insights, "12": self.delete_previous_insights,
                "13": self.display_analysis_results, "14": self.display_project_timeline,
                "15": self.analyze_badges, "16": self.retrieve_full_portfolio,
                "18": self.configure_personal_info, "19": self.create_report,
                "20": self.trigger_resume_generation, "21": self.trigger_portfolio_generation,
                "22": self.trigger_report_editing,"23": self.delete_report, "24": self.select_thumbnail,
                "98": self.compare_projects,"99": self.update_score_and_date,"100": self.edit_skills,
            }

            if choice == "17":
                print("Exiting Project Analyzer.")
                self._cleanup_temp()
                return

            if action := menu.get(choice):
                action()
            else:
                print("Invalid input. Try again.\n")
