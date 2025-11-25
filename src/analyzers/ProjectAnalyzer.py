import json
import os
import sys
import re
import shutil
import datetime
import contextlib
import zipfile
from src.ZipParser import parse, toString
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.FileCategorizer import FileCategorizer
from src.analyzers.language_detector import detect_language_per_file, analyze_language_share
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Dict
from src.analyzers.ContributionAnalyzer import ContributionAnalyzer, ContributionStats
from src.ZipParser import extract_zip
from utils.RepoFinder import RepoFinder
from src.ProjectManager import ProjectManager
from src.Project import Project
from src.generators.ResumeInsightsGenerator import ResumeInsightsGenerator
from src.ConfigManager import ConfigManager
from datetime import datetime


class ProjectAnalyzer:
    """
    Unified interface for analyzing zipped project files.
    Responsibilities:
    1. Git repo analysis + Contrib share
    2. Metadata and file statistics
    3. File categorization
    4. Folder tree printing
    5. Language detection
    6. Run all analyses
    7. Analyze New Folder
    8. Change Selected Users
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
        self.contribution_analyzer = ContributionAnalyzer()

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

        print("No authors found or selected. Skipping contribution analysis.")
        return None

    def _aggregate_stats(self, author_stats: Dict[str, ContributionStats], selected_authors: Optional[List[str]] = None) -> ContributionStats:
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

    def analyze_git_and_contributions(self):
        """
        Orchestrates the Git analysis workflow by running a single comprehensive
        analysis and then processing the results.
        """
        print("\n--- Git Repository & Contribution Analysis ---")
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
        """
        Extracts multiple Git repos from the ZIP, builds Projects, and prints
        resume insights (bullet points, summary, tech stack).
        Allows selecting another repo after each insights generation.
        """
        print("\nGenerating Resume Insights...\n")

        temp_dir = extract_zip(self.zip_path)
        self.cached_extract_dir = temp_dir

        try:
            repo_paths = self.repo_finder.find_repos(temp_dir)
            if not repo_paths:
                print("No Git repositories found.")
                return

            while True:
                # --- REPO SELECTION MENU ---
                selected_indices = self._select_repos(repo_paths)

                if not selected_indices:
                    # User chose "Return to menu"
                    break

                for idx in selected_indices:
                    project = self._build_project(repo_paths[idx])
                    if project:
                        self._print_resume_insights(project)

                # After finishing ONE repo, offer to choose another
                again = input("\nGenerate insights for another repository? (y/n): ").strip().lower()
                if again != "y":
                    break

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
            self.cached_extract_dir = None


    def _select_repos(self, repo_paths):
        if len(repo_paths) == 1:
            return [0]

        repo_names = [p.name for p in repo_paths]

        print("\nMultiple Git repositories detected:")
        for i, name in enumerate(repo_names, start=1):
            print(f" {i}. {name}")
        print(f"\n 0. ALL repositories")
        print(f" {len(repo_paths)+1}. Return to menu")

        choice = input("Choose: ").strip()

        if choice == str(len(repo_paths) + 1):
            return []

        if choice == "0":
            return list(range(len(repo_paths)))

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(repo_paths):
                return [idx]
        except:
            pass

        print("Invalid selection.")
        return []

    def _build_project(self, repo_path):
        repo_name = repo_path.name
        folder = self._find_folder_by_name(self.root_folder, repo_name)

        if folder is None:
            print(f"[ERROR] Could not locate folder for {repo_name}.")
            return None

        extractor = ProjectMetadataExtractor(folder)
        with self.suppress_output():
            metadata_full = extractor.extract_metadata()
        metadata = metadata_full["project_metadata"]
        categories = metadata_full["category_summary"]

        files = extractor.collect_all_files()
        repo_languages = sorted({
            detect_language_per_file(Path(f.file_name))
            for f in files
            if detect_language_per_file(Path(f.file_name))
        })

        language_share = analyze_language_share(str(repo_path))
        authors = self.contribution_analyzer.get_all_authors(str(repo_path))

        project = Project(
            name=repo_name,
            file_path=str(repo_path),
            root_folder=folder.name,
            authors=authors,
            author_count=len(authors),
            languages=repo_languages,
            collaboration_status="collaborative" if len(authors) > 1 else "individual"
        )

        project.metadata = metadata
        project.categories = categories
        project.language_share = language_share
        return project
    
    def _print_resume_insights(self, project):
        print("\n==============================")
        print(f" Resume Insights for: {project.name}")
        print("==============================\n")

        generator = ResumeInsightsGenerator(
            metadata=project.metadata,
            categorized_files=project.categories,
            language_share=project.language_share,
            language_list=project.languages,
            project=project,
        )

        print("Resume Bullet Points:")
        for b in generator.generate_resume_bullet_points():
            print(f" • {b}")
        print()

        print("Project Summary:")
        print(generator.generate_project_summary())
        print()


    def _find_folder_by_name(self, folder, target_name):
        """Recursively search the ZIP-parsed tree (ProjectFolder structure) for a folder by name."""
        if folder.name == target_name:
            return folder

        for sub in folder.subdir:
            found = self._find_folder_by_name(sub, target_name)
            if found:
                return found

        return None


    def analyze_new_folder(self):

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
        self.analyze_git_and_contributions()
        if self.root_folder:
            self.analyze_metadata()
            self.analyze_categories()
            self.print_tree()
            self.analyze_languages()
        print("\nAnalyses complete.\n")

    def run(self):
        print("Welcome to the Project Analyzer.\n")
        
        try:
            if not self.load_zip():
                return

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
                    9. Generate Resume Insights
                    10. Exit
                    """)

                choice = input ("Selection: ").strip()

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
                    self.analyze_new_folder()
                elif choice == "8":
                    self.change_selected_users()
                elif choice == "9":
                    self.generate_resume_insights()
                elif choice == "10":
                    print("Exiting Project Analyzer.")
                    # CLEAN UP TEMP DIR ON EXIT
                    if hasattr(self, "cached_extract_dir") and self.cached_extract_dir:
                        try:
                            shutil.rmtree(self.cached_extract_dir, ignore_errors=True)
                            self.cached_extract_dir = None
                        except Exception:
                            pass
                    return
                else:
                    print("Invalid input. Try again.\n")
        finally:
            if hasattr(self, "cached_extract_dir") and self.cached_extract_dir:
                shutil.rmtree(self.cached_extract_dir, ignore_errors=True)
                self.cached_extract_dir = None
