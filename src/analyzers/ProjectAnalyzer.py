import signal
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
from src.analyzers.ContributionAnalyzer import ContributionAnalyzer, ContributionStats
from utils.RepoFinder import RepoFinder
from src.ProjectManager import ProjectManager
from src.Project import Project
from src.ProjectFolder import ProjectFolder
from src.analyzers.SkillAnalyzer import SkillAnalyzer
from src.generators.ResumeInsightsGenerator import ResumeInsightsGenerator
from src.ConfigManager import ConfigManager
from src.ProjectRanker import ProjectRanker
from src.analyzers.RepoProjectBuilder import RepoProjectBuilder

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
        self.contribution_analyzer = ContributionAnalyzer()

        self.cached_extract_dir: Optional[Path] = None
        self.cached_projects: List[Project] = []

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

    def _ensure_scores_are_calculated(self) -> List[Project]:
        """
        Checks for projects with a zero score, runs skill analysis on them silently,
        and returns a complete list of all projects with their updated scores.
        """
        all_projects = self._get_projects()
        projects_needing_score = [p for p in all_projects if p.resume_score == 0]

        if projects_needing_score:
            print("\n  - Calculating resume scores for unscored projects...")
            self.analyze_skills(projects=projects_needing_score, silent=True)
            all_projects = self._get_projects()
            print("  - Score calculation complete.")

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
            proj_existing = self.project_manager.get_by_name(proj_new.name)
            if proj_existing:
                proj_existing.file_path, proj_existing.root_folder = proj_new.file_path, proj_new.root_folder
                self.project_manager.set(proj_existing)
                print(f"  - Updated existing project: {proj_existing.name}")
                created_projects.append(proj_existing)
            else:
                self.project_manager.set(proj_new)
                print(f"  - Created new project record: {proj_new.name} with ID {proj_new.id}")
                created_projects.append(proj_new)
        self.cached_projects = created_projects
        return created_projects

    # ------------------------------------------------------------------
    # Analysis Methods
    # ------------------------------------------------------------------

    def _prompt_for_usernames(self, authors: List[str]) -> Optional[List[str]]:
        print("\nPlease select your username(s) from the list of project contributors:")
        if not authors:
            print("No authors found in the commit history.")
            return None
        for i, author in enumerate(authors):
            print(f"  {i + 1}: {author}")
        print("\nYou can select multiple authors by entering numbers separated by commas (e.g., 1, 3).")
        try:
            choice_str = input("Enter your choice(s) (or 'q' to quit): ").strip()
            if choice_str.lower() == "q": return None
            selected_authors = []
            for choice in [c.strip() for c in choice_str.split(",")]:
                index = int(choice) - 1
                if not (0 <= index < len(authors)):
                    print(f"Invalid number '{choice}'. Please try again.")
                    return self._prompt_for_usernames(authors)
                selected_authors.append(authors[index])
            return sorted(list(set(selected_authors)))
        except (ValueError, IndexError):
            print("Invalid input format. Please enter numbers separated by commas.")
            return self._prompt_for_usernames(authors)
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

    def change_selected_users(self) -> None:
        """Allows the user to change their configured username selection."""
        print("\n--- Change Selected Users ---")
        projects = self._get_projects()
        if not projects: return
        all_authors = set()
        for project in projects:
            if (Path(project.file_path) / ".git").exists():
                with self.suppress_output():
                    all_authors.update(self.contribution_analyzer.get_all_authors(str(project.file_path)))
        if not all_authors:
            print("No Git authors found in any project.")
            return
        new_usernames = self._prompt_for_usernames(sorted(list(all_authors)))
        if new_usernames:
            self._config_manager.set("usernames", new_usernames)
            print(f"\nSuccessfully updated selected users to: {', '.join(new_usernames)}")
        else:
            print("\nNo changes made to user selection.")

    def analyze_git_and_contributions(self) -> None:
        print("\n--- Git Repository & Contribution Analysis ---")
        projects = self._get_projects()
        if not projects: return
        all_repo_authors, git_projects = set(), []
        for project in projects:
            if (Path(project.file_path) / ".git").exists():
                with self.suppress_output():
                    all_repo_authors.update(self.contribution_analyzer.get_all_authors(str(project.file_path)))
                git_projects.append(project)
        if not git_projects:
            print("No Git repositories found in the project list.")
            return

        selected_usernames = self._get_or_select_usernames(sorted(list(all_repo_authors)))
        if not selected_usernames: return

        for project in git_projects:
            print(f"\n--- Analyzing contributions for: {project.name} ---")
            all_author_stats = self.contribution_analyzer.analyze(str(project.file_path))
            if not all_author_stats: print(f"  - No contribution stats found."); continue

            project_authors = set(all_author_stats.keys())
            user_authors_in_project = sorted([name for name in selected_usernames if name in project_authors])

            project.authors = user_authors_in_project
            project.author_count = len(user_authors_in_project)
            project.collaboration_status = "collaborative" if project.author_count > 1 else "individual"

            selected_stats = self._aggregate_stats(all_author_stats, selected_usernames)
            total_stats = self._aggregate_stats(all_author_stats)
            project.author_contributions = [stats.to_dict() for stats in all_author_stats.values()]
            project.individual_contributions = self.contribution_analyzer.calculate_share(selected_stats, total_stats)

            project.last_accessed = datetime.now()
            self.project_manager.set(project)
            print(f"  - Saved contribution data for '{project.name}'.")

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
            if num_files := project_meta.get("total_files"): project.num_files = int(num_files)
            if size_kb := project_meta.get("total_size_kb"): project.size_kb = int(size_kb)
            if start_date := project_meta.get("start_date"): project.date_created = datetime.strptime(start_date, "%Y-%m-%d")
            if end_date := project_meta.get("end_date"): project.last_modified = datetime.strptime(end_date, "%Y-%m-%d")

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

            if not language_share: print("  - No languages detected."); continue
            for lang, share in language_share.items(): print(f"  - {lang}: {share:.1f}%")

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
                    if not silent: print(f"  - Warning: Path not found. Skipping.");
                    continue

                result = SkillAnalyzer(Path(project.file_path)).analyze()

                skills_raw = result.get("skills", [])
                filtered_skills = []
                for item in skills_raw:
                    name, conf = (item.get("skill"), item.get("confidence")) if isinstance(item, dict) else (getattr(item, 'skill', None), getattr(item, 'confidence', 0.0))
                    if name and conf >= MIN_DISPLAY_CONFIDENCE:
                        filtered_skills.append(name.strip())
                project.skills_used = sorted(list(set(filtered_skills)))

                if dimensions := result.get("dimensions", {}):
                    if td := dimensions.get("testing_discipline"): project.testing_discipline_score, project.testing_discipline_level = td.get("score", 0.0), td.get("level", "")
                    if doc := dimensions.get("documentation_habits"): project.documentation_habits_score, project.documentation_habits_level = doc.get("score", 0.0), doc.get("level", "")

                if overall := result.get("stats", {}).get("overall"):
                    project.total_loc, project.comment_ratio = overall.get("total_lines_of_code", 0), overall.get("comment_ratio", 0.0)

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

        # Ensure we have the necessary data for badge analysis
        if not all([project.num_files, project.date_created, project.last_modified, project.categories, project.languages, project.skills_used]):
            print(f"\n  - Prerequisite data missing for {project.name}. Running required analyses...")
            self.analyze_metadata(projects=[project])
            self.analyze_categories(projects=[project])
            self.analyze_languages(projects=[project])
            self.analyze_skills(projects=[project], silent=True)
            print(f"  - Prerequisite analyses complete for {project.name}.")
            # Re-fetch the project to get the updated data
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
                print(f"Could not find project '{project.name}' in ZIP structure."); return
            metadata = (ProjectMetadataExtractor(root_folder).extract_metadata(repo_path=project.file_path) or {}).get("project_metadata", {})

        gen = ResumeInsightsGenerator(
            metadata, project.categories, project.language_share, project, project.languages
        )

        project.bullets, project.summary = gen.generate_resume_bullet_points(), gen.generate_project_summary()
        self.project_manager.set(project)
        print(f"\nGenerated and saved insights for {project.name}:")
        gen.display_insights(project.bullets, project.summary)

    def generate_resume_insights(self) -> None:
        """Presents a menu to generate resume insights, ensuring scores are calculated first."""
        all_projects_with_scores = self._ensure_scores_are_calculated()

        scored_projects = [p for p in all_projects_with_scores if p.resume_score > 0]

        if not scored_projects:
            print("\nNo scored projects found to generate insights for. Please run 'Analyze Skills' first.")
            return

        sorted_projects = sorted(scored_projects, key=lambda p: p.resume_score, reverse=True)

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
                    self._generate_insights_for_project(proj)

                return

            except ValueError:
                print("Invalid input. Please enter a number.")
                continue

    def retrieve_previous_insights(self) -> None:
        print("\n--- Previous Resume Insights ---")
        for project in self._get_projects():
            if project.bullets or project.summary:
                print(f"\n{'='*20}\nInsights for: {project.name}\n{'='*20}")
                ResumeInsightsGenerator.display_insights(project.bullets, project.summary)

    def delete_previous_insights(self) -> None:
        """Deletes the stored resume insights for a user-selected project."""
        project = self._select_project("Select a project to delete insights from:")
        if not project:
            return
        project.bullets, project.summary = [], ""
        self.project_manager.set(project)
        print(f"Successfully deleted insights for {project.name}.")

    def display_project_timeline(self) -> None:
        print("\n--- Project & Skill Timeline ---")
        projects = self._get_projects()
        if not projects: return
        rows = get_projects_with_skills_timeline_from_projects(projects)
        print("\n=== Project Timeline (Chronological) ===")
        if not rows: print("No projects with valid dates found.")
        for when, name, skills in rows: print(f"{when.isoformat()} — {name}: {', '.join(skills) if skills else '(no skills)'}")
        events = get_skill_timeline_from_projects(projects)
        if not events: return
        print("\n=== Skill First-Use Timeline ===")
        first_seen = {ev.skill.lower(): ev for ev in reversed(events)}
        for ev in sorted(first_seen.values(), key=lambda e: (e.when, e.skill.lower())): print(f"{ev.when.isoformat()} — {ev.skill} (first seen in {ev.project or 'unknown'})")

    def display_analysis_results(self) -> None:
        print(f"\n{'=' * 30}\n      Analysis Results\n{'=' * 30}")
        all_projects = self._ensure_scores_are_calculated()
        scored_projects = [p for p in all_projects if p.resume_score > 0]

        if not scored_projects:
            print("\nNo projects with calculated scores to display.")
            return

        for project in scored_projects:
            project.display()

    def print_tree(self) -> None:
        print("\n--- Project Folder Structures ---")
        if not self.root_folders: print("No project structure loaded.")
        for root in self.root_folders: print(toString(root))

    def _cleanup_temp(self):
        if self.cached_extract_dir: shutil.rmtree(self.cached_extract_dir, ignore_errors=True)

    def _signal_cleanup(self, s, f):
        print("\n[Interrupted] Cleaning up..."); self._cleanup_temp(); sys.exit(0)

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
                16. Exit
                  """)

            choice = input("Selection: ").strip()

            if not self.zip_path and choice not in ["7", "16"]:
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
                "15": self.analyze_badges,
            }

            if choice == "16":
                print("Exiting Project Analyzer.")
                self._cleanup_temp()
                return

            if action := menu.get(choice):
                action()
            else:
                print("Invalid input. Try again.\n")
