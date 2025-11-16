import os
import shutil
from pathlib import Path
from typing import Iterable, Dict, Any, Set
from src.ZipParser import parse, toString, extract_zip
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.FileCategorizer import FileCategorizer
from src.analyzers.language_detector import detect_language_per_file, analyze_language_share
from utils.RepoFinder import RepoFinder
from src.ProjectManager import ProjectManager
from src.Project import Project
from src.analyzers.folder_skill_analyzer import FolderSkillAnalyzer
from src.analyzers.badge_engine import (
    ProjectAnalyticsSnapshot,
    assign_badges,
    build_fun_facts,
    aggregate_badges,
)


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

        self.folder_analyzer = FolderSkillAnalyzer()

    
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
            return []

        temp_dir = extract_zip(str(path_obj))
        try:
            projects = self.git_analyzer.run_analysis_from_path(temp_dir)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        # Optional: print summarized results here if desired
        return projects or []


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


        def run_all(self):
            print("Running All Analyzers\n")

            # 1) Git analysis – gives us Project objects with authors / collab info
            projects = self.analyze_git()
            current_project: Project | None = projects[0] if projects else None

            # 2) Metadata & category summary
            print("\nMetadata & File Statistics:")
            meta_payload = self.metadata_extractor.extract_metadata() or {}
            project_meta: Dict[str, Any] = meta_payload.get("project_metadata") or {}
            category_summary: Dict[str, Dict[str, Any]] = meta_payload.get("category_summary") or {}

            total_files = int(project_meta.get("total_files:", 0))
            total_size_kb = float(project_meta.get("total_size_kb:", 0.0))
            total_size_mb = float(project_meta.get("total_size_mb:", 0.0))
            duration_days = int(project_meta.get("duration_days:", 0))

            # 3) Language share + skills (filesystem-based, using the extracted zip)
            languages: Dict[str, float] = {}
            skills: Set[str] = set()

            if self.zip_path:
                path_obj = Path(self.zip_path)
                if path_obj.exists() and path_obj.suffix.lower() == ".zip":
                    temp_dir = extract_zip(str(path_obj))
                    try:
                        # language share
                        languages = analyze_language_share(temp_dir)

                        # skills via FolderSkillAnalyzer (top skills per folder)
                        self.folder_analyzer.analysis_results.clear()
                        self.folder_analyzer.analyze_folder(temp_dir)
                        for result in self.folder_analyzer.get_analysis_results():
                            for s in result["analysis_data"]["skills"]:
                                skills.add(s["skill"])
                    finally:
                        shutil.rmtree(temp_dir, ignore_errors=True)

            # 4) Author / collaboration info
            author_count = current_project.author_count if current_project else 1
            collaboration_status = (
                current_project.collaboration_status if current_project else "individual"
            )

            project_name = (
                current_project.name
                if current_project
                else (getattr(self.root_folder, "name", None) or "project")
            )

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

            # 5) Persist badges (and optionally languages/skills) on the Project record
            if current_project:
                current_project.badges = badge_ids
                current_project.languages = sorted(languages.keys())
                current_project.skills_used = sorted(skills)
                current_project.update_author_count()
                self.project_manager.set(current_project)

            # 6) Display project-level badges & fun facts
            print("\n=== BADGES FOR THIS PROJECT ===")
            if badge_ids:
                for b in badge_ids:
                    print(f"  - {b}")
            else:
                print("  (no badges assigned)")

            print("\n=== FUN FACTS ===")
            if fun_facts:
                for f in fun_facts:
                    print(f"  • {f}")
            else:
                print("  (no fun facts generated)")

            # 7) Existing analytics for this project
            self.analyze_categories()
            self.print_tree()
            self.analyze_languages()

            # 8) Portfolio-level badge summary across all projects (user profile view)
            all_projects = self.project_manager.get_all()
            badge_totals = aggregate_badges(all_projects)

            print("\n=== BADGE SUMMARY ACROSS ALL PROJECTS ===")
            if badge_totals:
                for badge_id, count in badge_totals.items():
                    print(f"  - {badge_id}: {count} project(s)")
            else:
                print("  (no badges recorded yet)")

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



    