import os
from src.ConsentManager import ConsentManager
from src.ZipParser import parse
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.FileCategorizer import FileCategorizer

def projectAnalyzer():
    zip_path = input("Please enter the path to the zipped folder: ")

    while not (os.path.exists(zip_path) and zip_path.endswith(".zip")):
        zip_path = input("Invalid path or not a zipped file. Please try again: ")

    git_repo_analyzer = GitRepoAnalyzer()
    project_metadata_extractor = ProjectMetadataExtractor()
    file_categorizer = FileCategorizer()

    user_selection = input("Please enter what you would like to do: \n1. Analyze git repo \n2. Extract folder metadata " \
    "\n3. Categorize zipped file types: \n4. Execute all")

    try:
        choice = int(user_selection.strip())
    except ValueError:
        print("Invalid selection.")
        return

    if choice == 1:
        print("Analyzing your Github repositories...")
        git_repo_analyzer.analyze_zip(zip_path)
        print("Git analysis complete.")
    elif choice == 2:
        print("Extracting folder metadata...")
        project_metadata_extractor.extract_metadata(zip_path)
        print("Project metadata extracted successfully.")
    elif choice == 3:
        print("Categorizing zipped file types...")
        file_categorizer.compute_metrics(zip_path)
    elif choice == 4:
        print("Starting analysis for all analyzers...")
        git_repo_analyzer.analyze_zip(zip_path)
        project_metadata_extractor.extract_metadata(zip_path)
        file_categorizer.compute_metrics(zip_path)
        print("Analyzers are all finished.")
    else:
        print("Invalid selection.")

    