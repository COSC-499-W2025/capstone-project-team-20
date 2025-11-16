import os
import shutil
from pathlib import Path
from typing import List

from src.ConsentManager import ConsentManager
from src.ZipParser import extract_zip
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from utils.RepoFinder import RepoFinder
from src.ProjectManager import ProjectManager
from src.Project import Project


def display_analysis_results(projects: List[Project]) -> None:
    """
    Prints the analysis results for a list of Project objects.

    Args:
        projects: The list of analyzed Project objects to display.
    """
    if not projects:
        print("\nNo analysis results to display.")
        return

    print("\n" + "="*30)
    print("      Analysis Results")
    print("="*30 + "\n")

    for project in sorted(projects, key=lambda p: p.name):
        print(f"Project: {project.name}")
        print("-" * (len(project.name) + 9))
        print(f"  - Authors ({project.author_count}): {', '.join(project.authors)}")
        print(f"  - Status: {project.collaboration_status}\n")
        # Will display other variables from Project classes in the future

def main():
    """
    Main application entry point. Handles user input and initiates the
    Git analysis workflow.
    """
    consent = ConsentManager()
    if not consent.require_consent():
        print("Consent not given. Exiting program.")
        return

    print("Consent confirmed. The application will now proceed.")

    zip_path_str = input("Please enter the path to the zip file to analyze: ").strip().strip("'\"")
    path_obj = Path(zip_path_str).expanduser()

    if not (path_obj.exists() and path_obj.suffix.lower() == '.zip'):
        print("Error: The provided path is invalid or is not a .zip file. Exiting.")
        return

    temp_dir: Path | None = None
    try:
        # Instantiate all dependencies here at the highest level.
        repo_finder = RepoFinder()
        project_manager = ProjectManager()
        git_analyzer = GitRepoAnalyzer(repo_finder, project_manager)

        print(f"Extracting archive: {path_obj}")
        temp_dir = extract_zip(str(path_obj))
        analyzed_projects = git_analyzer.run_analysis_from_path(temp_dir)
        display_analysis_results(analyzed_projects)

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
    finally:
        # --- Cleanup ---
        if temp_dir and temp_dir.exists() and temp_dir.is_dir():
            print(f"\nCleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir)
        print("\nProgram finished.")

if __name__ == "__main__":
    main()
