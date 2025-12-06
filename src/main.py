from src.ConsentManager import ConsentManager
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.ConfigManager import ConfigManager
from src.ProjectManager import ProjectManager
from src.Project import Project
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer

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

    initial_zip = ProjectAnalyzer.load_zip()
    root_folder, zip_path = initial_zip
    analyzer = ProjectAnalyzer(config_manager, root_folder, zip_path)
    analyzer.run()

if __name__ == "__main__":
    main()