import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager

def main():
    """
    Main entry point for the Project Analyzer application.
    Initializes the configuration and starts the analysis process.
    """
    config_manager = ConfigManager()


    # 1. Create an initial, empty analyzer instance.
    # We pass empty values because we will load the project next.
    initial_analyzer = ProjectAnalyzer(config_manager, root_folders=[], zip_path=None)

    # 2. Use the instance to call load_zip.
    try:
        root_folders, zip_path = initial_analyzer.load_zip()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting application.")
        return # Exit gracefully if the user cancels at the first prompt.

    # 3. If a project was loaded, create the final analyzer with the project data
    #    and start the main interactive loop.
    if zip_path and root_folders:
        analyzer = ProjectAnalyzer(config_manager, root_folders, zip_path)
        analyzer.run()
    else:
        print("No project loaded. Exiting.")

if __name__ == "__main__":
    main()
