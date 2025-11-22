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
    Responsibilities:
    1. Git repo analysis
    2. Metadata and file statistics
    3. File categorization
    4. Folder tree printing
    5. Language detection
    6. Run all analyses
    7. Analyze New Folder
    8. Display Previous Results
    9. Exit

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

    def analyze_git_and_contributions(self):
        """
        Orchestrates the entire Git analysis workflow, from project discovery to
        displaying aggregated contribution statistics.
        """
        print("\n--- Git Repository & Contribution Analysis ---")
        path_obj = Path(self.zip_path)
        if not path_obj.exists() or path_obj.suffix.lower() != ".zip":
            print(f"Error: {path_obj} is not a valid zip file.")
            return

        temp_dir = extract_zip(str(path_obj))
        try:
            # Step 1: Run initial Git analysis to find projects and authors.
            projects, authors = self.git_analyzer.run_analysis_from_path(temp_dir)
            self.display_analysis_results(projects)

            # Step 2: Handle user selection and configuration.
            usernames = self._config_manager.get("usernames")
            if not (usernames and isinstance(usernames, list)):
                if authors:
                    print("\nNo usernames found in configuration. Let's set them up.")
                    new_usernames = self._prompt_for_usernames(authors)
                    if new_usernames:
                        self._config_manager.set("usernames", new_usernames)
                        usernames = new_usernames
                        print(f"Usernames '{', '.join(usernames)}' have been saved.")
                    else:
                        print("No usernames were selected. Skipping contribution analysis.")
                        return
                else:
                    print("No authors found in repository. Skipping contribution analysis.")
                    return
            else:
                 print(f"\nWelcome back! Analyzing contributions for: {', '.join(usernames)}")

            # Step 3: Run contribution analysis using the configured usernames.
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

        finally:
            shutil.rmtree(temp_dir)

    def change_selected_users(self):
        """
        Allows the user to change their configured username selection.
        """
        print("\n--- Change Selected Users ---")
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
        print("      Project Analysis Results")
        print("="*30 + "\n")
        self._print_project(first_project)

        for project in projects_iter:
            self._print_project(project)


    def run_all(self):
        print("Running All Analyzers\n")
        self.analyze_git_and_contributions()
        if self.root_folder:
            self.analyze_metadata()
            self.analyze_categories()
            self.print_tree()
            self.analyze_languages()
        print("\nAnalyses complete.\n")

    def run(self):
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
                9. Exit
                  """)


            choice = input ("Selection: ").strip()

            if choice in {"1", "2", "3", "4", "5", "6", "7", "8"}:
                if not self.zip_path:
                    if not self.load_zip():
                        return

            if choice == "1":
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
                print ("\nLoading new project...")
                if self.load_zip():
                    print("New project loaded successfully\n")
                else:
                    print("Failed to load new project\n")
            elif choice == "8":
                self.change_selected_users()
            elif choice == "9":
                print("Exiting Project Analyzer.")
                return
            else:
                print("Invalid input. Try again.\n")
