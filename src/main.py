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

    # The user can uncomment the following line for testing purposes
    # to reset the saved usernames and trigger the selection prompt.
    # config_manager.delete("usernames")

    while True:
        if consent.require_consent():
            break
        print("Consent is required to run the program. Please try again.\n")

    # Pass the config_manager instance to the analyzer
    analyzer = ProjectAnalyzer(config_manager=config_manager)
    analyzer.run()

if __name__ == "__main__":
    main()
