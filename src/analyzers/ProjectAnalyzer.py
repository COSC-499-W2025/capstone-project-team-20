import os
import shutil
from src.ZipParser import parse, toString
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.FileCategorizer import FileCategorizer
from src.analyzers.language_detector import detect_language_per_file
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.analyzers.ContributionAnalyzer import ContributionAnalyzer, ContributionStats
from src.ZipParser import extract_zip
from utils.RepoFinder import RepoFinder
from src.ProjectManager import ProjectManager
from src.Project import Project
from src.ConfigManager import ConfigManager


class ProjectAnalyzer:
    """
    Unified interface for analyzing zipped project files.
    """

    def __init__(self, config_manager: ConfigManager):
        self.root_folder = None
        self.zip_path = None
        self._config_manager = config_manager
        self.metadata_extractor = ProjectMetadataExtractor(self.root_folder)
        self.file_categorizer = FileCategorizer()
        self.repo_finder = RepoFinder()
        self.project_manager = ProjectManager()
        self.git_analyzer = GitRepoAnalyzer(self.repo_finder, self.project_manager)
        self.contribution_analyzer = ContributionAnalyzer()

    def _print_project(self, project: Project) -> None:
            print(f"Project: {project.name}")
            print("-" * (len(project.name) + 9))
            print(f"  - Authors ({project.author_count}): {', '.join(project.authors)}")
            print(f"  - Status: {project.collaboration_status}\n")

    def load_zip(self):
        """Prompts user for ZIP file and parses into folder tree"""
        zip_path = input("Please enter the path to the zipped folder: ")
        zip_path = os.path.expanduser(zip_path)
        while not (os.path.exists(zip_path) and zip_path.endswith(".zip")):
            zip_path = input("Invalid path or not a zipped file. Please try again: ")

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

    def analyze_git(self):
        """
        Analyzes git repositories, and handles user selection.
        """
        print("\nGit repository Analysis")
        path_obj = Path(self.zip_path)
        if not path_obj.exists() or path_obj.suffix.lower() != ".zip":
            print(f"Error: {path_obj} is not a valid zip file.")
            return

        temp_dir = extract_zip(str(path_obj))
        try:
            projects, authors = self.git_analyzer.run_analysis_from_path(temp_dir)
            self.display_analysis_results(projects)

            usernames = self._config_manager.get("usernames")
            if usernames and isinstance(usernames, list):
                print(f"\nWelcome back! Using configured usernames: {', '.join(usernames)}")
            elif authors:
                print("\nNo usernames found in configuration. Let's set them up.")
                new_usernames = self._prompt_for_usernames(authors)
                if new_usernames:
                    self._config_manager.set("usernames", new_usernames)
                    print(f"Usernames '{', '.join(new_usernames)}' have been saved.")
                else:
                    print("No usernames were selected.")
        finally:
            shutil.rmtree(temp_dir)

    def analyze_contributions(self):
        """
        Analyzes and displays the contributions of configured users.
        """
        print("\nAnalyzing User Contributions...")
        usernames = self._config_manager.get("usernames")
        if not usernames or not isinstance(usernames, list):
            print("No usernames are configured. Please run Git Analysis (1) first to select users.")
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

            selected_stats, total_stats = self.contribution_analyzer.analyze(str(repo_paths[0]), usernames)
            self._display_contribution_results(selected_stats, total_stats, usernames)

        finally:
            shutil.rmtree(temp_dir)

    def _display_contribution_results(self, selected_stats: ContributionStats, total_stats: ContributionStats, usernames: List[str]):
        """Formats and prints the aggregated contribution analysis results."""

        header = f"Contribution Share for: {', '.join(usernames)}"
        print("\n" + "="*80)
        print(f"{header:^80}")
        print("="*80)

        total_lines_edited_project = total_stats.lines_added + total_stats.lines_deleted
        total_lines_edited_selected = selected_stats.lines_added + selected_stats.lines_deleted

        if total_lines_edited_project > 0:
            project_share = (total_lines_edited_selected / total_lines_edited_project) * 100
            print(f"\nCollectively, you contributed {project_share:.2f}% of the total lines edited in the project.")
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
            for type, count in selected_stats.contribution_by_type.items():
                percentage = (count / total_lines_by_type) * 100
                print(f"    - {type.capitalize():<5}: {percentage:6.2f}%")
        print("\n" + "="*80)


    def analyze_metadata(self):
        print("\nMetadata & File Statistics:")
        self.metadata_extractor.extract_metadata()

    def analyze_categories(self):
        print("File Categories")
        files = self.metadata_extractor.collect_all_files()
        file_dicts = [
            {"path":f.file_name, "language": getattr(f, "language", "Unknown")}
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

    def display_analysis_results(self, projects: Iterable[Project]) -> None:
        """
        Prints the analysis results for a list of Project objects.
        """
        projects_iter = iter(projects)
        try:
            first_project = next(projects_iter)
        except StopIteration:
            print("\nNo analysis results to display.")
            return
        print("\n" + "="*30)
        print("      Analysis Results")
        print("="*30 + "\n")
        self._print_project(first_project)

        for project in projects_iter:
            self._print_project(project)


    def run_all(self):
        print("Running All Analyzers\n")
        self.analyze_git()
        if self.root_folder:
            self.analyze_metadata()
            self.analyze_categories()
            self.print_tree()
            self.analyze_languages()
        # Contribution analysis is not run by default, as it's a specific query.
        print("\nAnalyses complete.\n")

    def run(self):
        while True:
            # Menu is expanded with the new option.
            print("""
                ========================
                Project Analyzer
                ========================
                Choose an option:
                1. Analyze Git Repository (and Select Users)
                2. Analyze User Contributions
                3. Extract Metadata & File Statistics
                4. Categorize Files by Type
                5. Print Project Folder Structure
                6. Analyze Languages Detected
                7. Run All General Analyses
                8. Analyze New Folder
                9. Display Previous Results
                10. Exit
                  """)


            choice = input ("Selection: ").strip()

            if choice in {"1", "2", "3", "4", "5", "6", "7", "8"}:
                if not self.zip_path:
                    if not self.load_zip():
                        return

            if choice == "1":
                self.analyze_git()
            elif choice == "2":
                self.analyze_contributions()
            elif choice == "3":
                self.analyze_metadata()
            elif choice == "4":
                self.analyze_categories()
            elif choice == "5":
                self.print_tree()
            elif choice == "6":
                self.analyze_languages()
            elif choice == "7":
                self.run_all()
            elif choice == "8":
                print ("\nLoading new project...")
                if self.load_zip():
                    print("New project loaded successfully\n")
                else:
                    print("Failed to load new project\n")
            elif choice == "9":
                projects = self.project_manager.get_all()
                self.display_analysis_results(projects)
            elif choice == "10":
                print("Exiting Project Analyzer.")
                return
            else:
                print("Invalid input. Try again.\n")
