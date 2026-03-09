from src.managers.ConsentManager import ConsentManager
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager

def main():
    """
    Main application entry point. Handles user input and initiates the
    Git analysis workflow.
    """
    consent = ConsentManager()
    config_manager = ConfigManager()

    # Consent loop
    while True:
        if consent.require_consent():
            break
        print("Consent is required to run the program. Please try again.\n")

    # Load ZIP
    root_folders, zip_path = ProjectAnalyzer.load_zip()

    if not root_folders:
        print("Could not find any projects in the ZIP file. Exiting.")
        return

    analyzer = ProjectAnalyzer(config_manager, root_folders, zip_path)

    # Initialize + run all analyses
    analyzer.initialize_projects()
    analyzer.run_all()

    # Enter interactive mode
    analyzer.run()

if __name__ == "__main__":
    main()
