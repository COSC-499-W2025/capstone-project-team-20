from src.ConsentManager import ConsentManager
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.ConfigManager import ConfigManager

def main():
    """
    Main application entry point. Handles user input and initiates the
    Git analysis workflow.
    """
    consent = ConsentManager()
    config_manager = ConfigManager()

    while True:
        if consent.require_consent():
            break
        print("Consent is required to run the program. Please try again.\n")

    # 1. Load the ZIP file a single time.
    root_folders, zip_path = ProjectAnalyzer.load_zip()
    if not root_folders:
        print("Could not find any projects in the ZIP file. Exiting.")
        return

    # 2. Create the analyzer instance with the loaded data.
    analyzer = ProjectAnalyzer(config_manager, root_folders, zip_path)

    # 3. Initialize the projects from the ZIP before showing the menu.
    analyzer.initialize_projects()

    # 4. Start the interactive menu loop.
    analyzer.run()

if __name__ == "__main__":
    main()
