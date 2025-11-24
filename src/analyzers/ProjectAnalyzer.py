import datetime
import os, sys, contextlib, shutil
from src.ZipParser import parse, toString
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.FileCategorizer import FileCategorizer
from src.analyzers.language_detector import detect_language_per_file, analyze_language_share
from pathlib import Path
from typing import Iterable
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.ZipParser import extract_zip
from utils.RepoFinder import RepoFinder
from src.ProjectManager import ProjectManager
from src.Project import Project
from src.generators.ResumeInsightsGenerator import ResumeInsightsGenerator

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

    def __init__(self):
        self.root_folder = None
        self.zip_path = None
        self.metadata_extractor = ProjectMetadataExtractor(self.root_folder)
        self.file_categorizer = FileCategorizer()
        self.repo_finder = RepoFinder()
        self.project_manager = ProjectManager()
        self.git_analyzer = GitRepoAnalyzer(self.repo_finder, self.project_manager)

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
            # Will display other variables from Project classes in the future

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

    def analyze_git(self):
        print("\nGit repository Analysis")
        path_obj = Path(self.zip_path)
        if not path_obj.exists() or path_obj.suffix.lower() != ".zip":
            print(f"Error: {path_obj} is not a valid zip file.")
            return
        
        temp_dir = extract_zip(str(path_obj))
        try:
            self.git_analyzer.run_analysis_from_path(temp_dir)
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
        """
        Prints the analysis results for a list of Project objects.

        Args:
            projects: The list of analyzed Project objects to display.
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


    def generate_resume_insights(self):
        print("\nGenerating Resume Insights...\n")

        # 0. Cache ONLY Git repo scan results (never metadata)
        if getattr(self, "cached_projects", None) is not None:
            projects = self.cached_projects
        else:
            # Extract ZIP once
            if getattr(self, "cached_extract_dir", None) is None:
                self.cached_extract_dir = extract_zip(self.zip_path)

            extract_dir = self.cached_extract_dir

            with self.suppress_output():
                projects = self.git_analyzer.run_analysis_from_path(extract_dir)

            self.cached_projects = projects

        if not projects:
            print("No Git projects found. Cannot generate insights.")
            return

        # ---- Project selection loop ----
        while True:
            print("\nMultiple Git projects detected:")
            for i, proj in enumerate(projects, start=1):
                print(f" {i}. {proj.name}")

            return_option = len(projects) + 1
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
                selected = projects
            else:
                try:
                    idx = int(choice) - 1
                    if idx < 0 or idx >= len(projects):
                        print("Invalid selection.\n")
                        continue
                    selected = [projects[idx]]
                except ValueError:
                    print("Invalid input.\n")
                    continue

            # ---- Analyze each selected repo using ZIP folder tree ----
            for proj in selected:
                print("\n==============================")
                print(f" Resume Insights for: {proj.name}")
                print("==============================\n")

                # Force resume insights to use the same root folder the metadata system uses
                # --- Determine correct folder for this project ---
                if len(projects) == 1:
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
                print("DEBUG METADATA SUMMARY:", metadata_full["category_summary"])

                # 4.language detector
                language_share = analyze_language_share(
                    self.cached_extract_dir / proj.name
                    )
                
                repo_languages = set()

                for f in files:
                    lang = detect_language_per_file(Path(f.file_name))
                    if lang:
                        repo_languages.add(lang)

                repo_languages = sorted(repo_languages)

                # 5. Generate resume insights
                generator = ResumeInsightsGenerator(
                    metadata=metadata,
                    categorized_files=categorized_files,
                    language_share=language_share,
                    language_list = repo_languages,
                    project=proj
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
        self.analyze_metadata()
        self.analyze_categories()
        self.print_tree()
        self.analyze_languages()
        print("\nAnalyses complete.\n")

    def run(self):
        print("Welcome to the Project Analyzer.\n")

        if not self.load_zip():
            return

        while True:
            print("""
                =================
                Project Analyzer
                =================
                Choose an option:
                1. Analyze Git Repository
                2. Extract Metadata & File Statistics
                3. Categorize Files by Type
                4. Print Project Folder Structure
                5. Analyze Languages Detected
                6. Run All Analyses
                7. Analyze New Folder
                8. Display Previous Results
                9. Generate Resume Insights
                10. Exit
                  """)

    
            choice = input ("Selection: ").strip()

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
                projects = self.project_manager.get_all()
                self.display_analysis_results(projects)
            elif choice == "9":
                self.generate_resume_insights()
            elif choice == "10":
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



    