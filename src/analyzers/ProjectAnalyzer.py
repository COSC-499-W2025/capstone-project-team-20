import os
from src.ZipParser import parse, toString
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.FileCategorizer import FileCategorizer
from src.analyzers.language_detector import detect_language

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
    """

    def __init__(self):
        self.root_folder = None
        self.zip_path = None
        self.metadata_extractor = ProjectMetadataExtractor(self.root_folder)
        self.file_categorizer = FileCategorizer()
        self.git_analyzer = GitRepoAnalyzer()

    def load_zip(self):
        """Prompts user for ZIP file and parses into folder tree"""
        zip_path = input("Please enter the path to the zipped folder: ")
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
        self.git_analyzer.analyze_zip(self.zip_path)

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
        langs = {
            detect_language([f.file_name])
            for f in files
            if detect_language([f.file_name]) != "Unknown"
        }

        if not langs:
            print("No languages detected")
            return
        
        for lang in sorted(langs):
            print(f" - {lang}")

    def run_all(self):
        print("Running All Analyzers\n")
        self.analyze_git()
        self.analyze_metadata()
        self.analyze_categories()
        self.print_tree
        self.analyze_languages()
        print("\nAnalyses complete.\n")

    def run(self):
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
                7. Exit
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
                print("Exiting Project Analyzer.")
                return
            else:
                print("Invalid input. Try again.\n")



    