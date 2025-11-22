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
from src.analyzers.skill_analyzer import SkillAnalyzer
from src.analyzers.code_metrics_analyzer import CodeMetricsAnalyzer


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
    
    def analyze_skills(self):
        """
        Run skill analysis on the currently loaded zip project.

        This:
        - Extracts the zip to a temporary directory,
        - Runs SkillAnalyzer (which internally runs CodeMetricsAnalyzer),
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

            # 🔹 NEW: persist metrics into the Project record
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

            # Primary languages + tools etc. could be printed here

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

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


    def run_all(self):
        print("Running All Analyzers\n")
        self.analyze_git()
        self.analyze_metadata()
        self.analyze_categories()
        self.print_tree()
        self.analyze_languages()
        self.analyze_skills()
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
                9. Analyze Skills
                10. Exit
                  """)

    
            choice = input ("Selection: ").strip()

            if choice in {"1", "2", "3", "4", "5", "6", "9"}:
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
                print("\nLoading new project...")
                self.zip_path = None
                if self.load_zip():
                    print("New project loaded successfully\n")
                else:
                    print("Failed to load new project\n")
            elif choice == "8":
                projects = self.project_manager.get_all()
                self.display_analysis_results(projects)
            elif choice == "9":
                self.analyze_skills()
            elif choice == "10":
                print("Exiting Project Analyzer.")
                return
            else:
                print("Invalid input. Try again.\n")



    