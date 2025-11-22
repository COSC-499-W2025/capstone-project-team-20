import os
import shutil
from src.ZipParser import parse, toString
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.FileCategorizer import FileCategorizer
from src.analyzers.language_detector import detect_language_per_file
from pathlib import Path
from typing import Iterable
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.ZipParser import extract_zip
from utils.RepoFinder import RepoFinder
from src.ProjectManager import ProjectManager
from src.Project import Project

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
    
    def _print_project(self, project: Project) -> None:
            print(f"Project: {project.name}")
            print("-" * (len(project.name) + 9))
            print(f"  - Authors ({project.author_count}): {', '.join(project.authors)}")
            print(f"  - Status: {project.collaboration_status}\n")
            # Will display other variables from Project classes in the future

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
        projects_list = list(projects)
        if not projects_list:
            print("\nNo analysis results to display.")
            return
        
        print(f"\n{'='*30}")
        print("      Analysis Results")
        print(f"{'='*30}")
        
        for project in projects_list:
            project.display()


    def run_all(self):
        print("Running All Analyzers\n")
        self.analyze_git()
        self.analyze_metadata()
        self.analyze_categories()
        self.print_tree()
        self.analyze_languages()
        print("\nAnalyses complete.\n")

    def run(self):
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
                9. Exit
                  """)

    
            choice = input ("Selection: ").strip()

            if choice in {"1", "2", "3", "4", "5", "6", "7"}:
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
                print ("\nLoading new project...")
                if self.load_zip():
                    print("New project loaded successfully\n")
                else:
                    print("Failed to load new project\n")
            elif choice == "8":
                projects = self.project_manager.get_all()
                self.display_analysis_results(projects)
            elif choice == "9":
                print("Exiting Project Analyzer.")
                return
            else:
                print("Invalid input. Try again.\n")



    