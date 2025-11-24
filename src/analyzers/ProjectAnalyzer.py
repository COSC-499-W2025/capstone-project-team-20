import os
import sys
import re
import shutil
import datetime
import contextlib
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional

from src.ZipParser import parse, toString, extract_zip
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.FileCategorizer import FileCategorizer
from src.analyzers.language_detector import detect_language_per_file, analyze_language_share
from utils.RepoFinder import RepoFinder
from src.ProjectManager import ProjectManager
from src.Project import Project
from src.analyzers.skill_analyzer import SkillAnalyzer
from src.analyzers.code_metrics_analyzer import CodeMetricsAnalyzer
from src.generators.ResumeInsightsGenerator import ResumeInsightsGenerator
from src.ConfigManager import ConfigManager


class ProjectAnalyzer:
    """
    Unified interface for analyzing zipped project files.
    Responsibilities:
    1. Git repo analysis
    2. Metadata and file statistics
    3. File categorization
    4. Folder tree printing
    5. Language detection
    6. Run all analyses
    7. Analyze New Folder
    8. Display Previous Results
    9. Analyze Skills
    10. Generate Resume Insights
    11. Exit
    """

    def __init__(self, config_manager: ConfigManager):
        self.root_folder = None
        self.zip_path: Optional[Path] = None
        self._config_manager = config_manager

        self.metadata_extractor = ProjectMetadataExtractor(self.root_folder)
        self.file_categorizer = FileCategorizer()
        self.repo_finder = RepoFinder()
        self.project_manager = ProjectManager()
        self.git_analyzer = GitRepoAnalyzer(self.repo_finder, self.project_manager)

        # Caches used primarily for resume insight generation
        self.cached_extract_dir: Optional[Path] = None
        self.cached_projects: Optional[Iterable[Project]] = None

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
        # Remove shell escape backslashes (e.g., "my\ file" -> "my file")
        unescaped = re.sub(r'\\(.)', r'\1', stripped)
        return Path(os.path.expanduser(unescaped))

    def batch_analyze(self, zipped_repos_dir: str = 'zipped_repos') -> None:
        """
        Loops through all zipped repositories in a directory (`zipped_repos/` by default) and calls run_all(). Called from utils/analyze_repos.py
        """
        zipped_repos_path = Path(zipped_repos_dir)
        if not zipped_repos_path.exists():
            print(f"Nothing to analyze - {zipped_repos_dir}/ doesn't exist")
            return
        
        zip_files = list(zipped_repos_path.rglob('*.zip'))
        if not zip_files:
            print(f"No .zip files found in {zipped_repos_dir}/")
            return
        
        print(f"\nBatch analyzing {len(zip_files)} repositories...\n")
        analyzed, failed = 0, 0

        for zip_path in zip_files:
            repo_name = zip_path.stem
            try:
                self.zip_path = str(zip_path)
                self.root_folder = parse(self.zip_path)
                self.metadata_extractor = ProjectMetadataExtractor(self.root_folder)
                print(f"\n{'='*50}")
                print(f"Analyzing: {repo_name}")
                print(f"{'='*50}")
                self.run_all()
                analyzed += 1

            except Exception as e:
                print(f"❌ {repo_name}: {str(e)[:50]}")
                failed += 1

        print(f"\n{'='*40}")
        print(f"Analyzed: {analyzed} | Failed: {failed}")
        print(f"{'='*40}\n")

    def load_zip(self):
        """Prompts user for ZIP file and parses into folder tree"""
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

            if choice_str.lower() == 'q':
                print("Aborting user selection.")
                return None

            selected_authors = []
            choices = [c.strip() for c in choice_str.split(',')]
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

        print("No authors found or selected.")
        return None

    def analyze_git(self):
        """Analyzes git repositories and handles user selection."""
        print("\nGit repository Analysis")
        if not self.zip_path:
            print("No project loaded. Please load a zip file first.\n")
            return

        path_obj = Path(self.zip_path)
        if not path_obj.exists() or path_obj.suffix.lower() != ".zip":
            print(f"Error: {path_obj} is not a valid zip file.")
            return

        temp_dir = extract_zip(str(path_obj))
        try:
            projects, authors = self.git_analyzer.run_analysis_from_path(temp_dir)
            self.display_analysis_results(projects)

            # Handle username selection and configuration
            self._get_or_select_usernames(authors)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def change_selected_users(self):
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
            # Get authors from the repository
            _, authors = self.git_analyzer.run_analysis_from_path(temp_dir)

            print("Please select the new set of usernames you would like to use.")
            new_usernames = self._prompt_for_usernames(authors)

            if new_usernames:
                self._config_manager.set("usernames", new_usernames)
                print(f"\nSuccessfully updated selected users to: {', '.join(new_usernames)}")
            else:
                print("\nNo changes made to user selection.")
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def analyze_metadata(self):
        print("\nMetadata & File Statistics:")
        self.metadata_extractor.extract_metadata()

    def analyze_categories(self):
        print("File Categories")
        files = self.metadata_extractor.collect_all_files()
        file_dicts = [
            {"path": f.file_name, "language": getattr(f, "language", "Unknown")}
            for f in files
        ]
        result = self.file_categorizer.compute_metrics(file_dicts)
        print(result)

    def print_tree(self):
        print("Project Folder Structure")
        print(toString(self.root_folder))

    def analyze_languages(self):
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

    def analyze_skills(self):
        """
        Run skill analysis on the currently loaded zip project.

        This:
        - Extracts the zip to a temporary directory,
        - Runs SkillAnalyzer (which internally may run CodeMetricsAnalyzer),
        - Prints a human-readable summary of detected skills,
        - Persists key metrics onto the corresponding Project in the DB.
        """
        if not self.zip_path:
            print("No project loaded. Please load a zip file first.\n")
            return

        path_obj = Path(self.zip_path)
        if not path_obj.exists() or path_obj.suffix.lower() != ".zip":
            print(f"Error: {path_obj} is not a valid zip file.")
            return

        print("\nSkill Analysis (languages, frameworks, tooling):")
        temp_dir = extract_zip(str(path_obj))
        try:
            skill_analyzer = SkillAnalyzer(Path(temp_dir))
            result = skill_analyzer.analyze()
            skills = result.get("skills", [])
            stats = result.get("stats", {})
            dimensions = result.get("dimensions", {})

            if not skills:
                print("No skills could be inferred from this project.")
                return

            overall = stats.get("overall", {})
            per_lang = stats.get("per_language", {})

            # Persist metrics into the Project record
            project_name = Path(self.zip_path).stem
            project = self.project_manager.get_by_name(project_name)

            if project is not None:
                # Overall metrics
                project.total_loc = overall.get("total_loc", 0)
                project.comment_ratio = overall.get("comment_ratio", 0.0)
                project.test_file_ratio = overall.get("test_file_ratio", 0.0)
                project.avg_functions_per_file = overall.get("avg_functions_per_file", 0.0)
                project.max_function_length = overall.get("max_function_length", 0)

                # Primary languages by LOC (ignore tiny ones)
                project.primary_languages = [
                    lang
                    for lang, data in sorted(
                        per_lang.items(),
                        key=lambda kv: kv[1].get("loc", 0),
                        reverse=True,
                    )
                    if data.get("loc", 0) >= 100
                ]

                # Dimensions
                td = dimensions.get("testing_discipline", {})
                project.testing_discipline_level = td.get("level", "")
                project.testing_discipline_score = td.get("score", 0.0)

                doc = dimensions.get("documentation_habits", {})
                project.documentation_habits_level = doc.get("level", "")
                project.documentation_habits_score = doc.get("score", 0.0)

                mod = dimensions.get("modularity", {})
                project.modularity_level = mod.get("level", "")
                project.modularity_score = mod.get("score", 0.0)

                ld = dimensions.get("language_depth", {})
                project.language_depth_level = ld.get("level", "")
                project.language_depth_score = ld.get("score", 0.0)

                # Save back to DB
                self.project_manager.set(project)

            # --- Printing / user-facing output ---
            print("\nProject-level code metrics:")
            for k, v in overall.items():
                print(f"  - {k}: {v}")

            # You could also print skill list and dimensions here if desired.

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def display_analysis_results(self, projects: Iterable[Project]) -> None:
        projects_list = list(projects)
        if not projects_list:
            print("\nNo analysis results to display.")
            return
        
        print(f"\n{'='*30}")
        print("      Analysis Results")
        print(f"{'='*30}")
        
        for project in projects_list:
            project.display()

    def generate_resume_insights(self):
        print("\nGenerating Resume Insights...\n")

        # 0. Cache ONLY Git repo scan results (never metadata)
        if getattr(self, "cached_projects", None) is not None:
            projects = self.cached_projects
        else:
            if not self.zip_path:
                print("No project loaded. Please load a zip file first.\n")
                return

            # Extract ZIP once
            if getattr(self, "cached_extract_dir", None) is None:
                self.cached_extract_dir = Path(extract_zip(self.zip_path))

            extract_dir = self.cached_extract_dir

            with self.suppress_output():
                projects, _authors = self.git_analyzer.run_analysis_from_path(extract_dir)

            self.cached_projects = projects

        if not projects:
            print("No Git projects found. Cannot generate insights.")
            return

        # ---- Project selection loop ----
        while True:
            print("\nMultiple Git projects detected:")
            projects_list = list(projects)
            for i, proj in enumerate(projects_list, start=1):
                print(f" {i}. {proj.name}")

            return_option = len(projects_list) + 1
            print("\nSelect an option:")
            print(" 0. Generate insights for ALL projects")
            print(f" {return_option}. Return to Main Menu")

            choice = input("Choose a project number: ").strip()

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

            if choice == "0":
                selected = projects_list
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

            # ---- Analyze each selected repo using ZIP folder tree ----
            for proj in selected:
                print("\n==============================")
                print(f" Resume Insights for: {proj.name}")
                print("==============================\n")

                # Determine correct folder for this project
                if len(projects_list) == 1:
                    # Solo repo → use entire ZIP content
                    folder = self.root_folder
                else:
                    # Multi-repo ZIP → find the subfolder that matches the repo
                    folder = self._find_folder_by_name(self.root_folder, proj.name)

                    if folder is None:
                        print(f"[ERROR] Could not locate the folder for repo '{proj.name}' inside the ZIP.")
                        print("Skipping this project to avoid incorrect global counts.\n")
                        continue

                extractor = ProjectMetadataExtractor(folder)
                with self.suppress_output():
                    metadata_full = extractor.extract_metadata()
                metadata = metadata_full["project_metadata"]
                files = extractor.collect_all_files()

                # Categorization input
                categorized_files = metadata_full["category_summary"]

                # Language detector
                language_share = analyze_language_share(
                    Path(self.cached_extract_dir) / proj.name
                )

                repo_languages = set()
                for f in files:
                    lang = detect_language_per_file(Path(f.file_name))
                    if lang:
                        repo_languages.add(lang)

                repo_languages = sorted(repo_languages)

                # Generate resume insights
                generator = ResumeInsightsGenerator(
                    metadata=metadata,
                    categorized_files=categorized_files,
                    language_share=language_share,
                    language_list=repo_languages,
                    project=proj,
                )

                bullets = generator.generate_resume_bullet_points()
                summary = generator.generate_project_summary()

                print("Resume Bullet Points:")
                for b in bullets:
                    print(f" • {b}")

                print("\nProject Summary:")
                print(summary)
                print("\n")

    def _find_folder_by_name(self, folder, target_name):
        """Recursively search the ZIP-parsed tree for a folder that matches a repo name."""
        if folder.name == target_name:
            return folder

        for sub in folder.subdir:
            found = self._find_folder_by_name(sub, target_name)
            if found:
                return found

        return None

    def analyze_new_folder(self):
        """Reset caches and load a new ZIP project."""
        if hasattr(self, "cached_extract_dir") and self.cached_extract_dir:
            try:
                shutil.rmtree(self.cached_extract_dir, ignore_errors=True)
            except Exception:
                pass
            self.cached_extract_dir = None

        self.cached_projects = None

        print("\nLoading new project...")
        success = self.load_zip()

        if success:
            print("\nNew project loaded successfully\n")
        else:
            print("\nFailed to load new project.\n")

    def run_all(self):
        print("Running All Analyzers\n")
        self.analyze_git()
        if self.root_folder:
            self.analyze_metadata()
            self.analyze_categories()
            self.print_tree()
            self.analyze_languages()
        self.analyze_skills()
        print("\nAnalyses complete.\n")

    def run(self):
        print("Welcome to the Project Analyzer.\n")

        if not self.load_zip():
            return

        while True:
            print("""
                ========================
                Project Analyzer
                ========================
                Choose an option:
                1. Analyze Git Repository
                2. Extract Metadata & File Statistics
                3. Categorize Files by Type
                4. Print Project Folder Structure
                5. Analyze Languages Detected
                6. Run All Analyses
                7. Analyze New Folder
                8. Display Previous Results
                9. Analyze Skills
                10. Generate Resume Insights
                11. Display Previous Results
                12. Exit
                  """)

            choice = input("Selection: ").strip()

            # For options that require a loaded ZIP, ensure we have one
            if choice in {"1", "2", "3", "4", "5", "6", "8", "9", "10"}:
                if not self.zip_path:
                    if not self.load_zip():
                        return

            if choice == "1":
                self.analyze_git()
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
            elif choice == "8":
                self.change_selected_users()
            elif choice == "9":
                self.analyze_skills()
            elif choice == "10":
                self.generate_resume_insights()
            elif choice == "11":
                projects = self.project_manager.get_all()
                self.display_analysis_results(projects)
            elif choice == "12":
                print("Exiting Project Analyzer.")
                # CLEAN UP TEMP DIR ON EXIT
                if hasattr(self, "cached_extract_dir") and self.cached_extract_dir:
                    try:
                        shutil.rmtree(self.cached_extract_dir, ignore_errors=True)
                    except Exception:
                        pass
                return
            else:
                print("Invalid input. Try again.\n")
