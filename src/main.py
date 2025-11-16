from src.ConsentManager import ConsentManager
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer

def main():
    """
    Main application entry point. Handles user input and initiates the
    Git analysis workflow.
    """
    consent = ConsentManager()

    # Reset for testing if needed, uncomment two lines below
    # from src.ConfigManager import ConfigManager
    # ConfigManager().delete("user_consent")

    while True:
        if consent.require_consent():
            break
        print("Consent is required to run the program. Please try again.\n")
    
    analyzer = ProjectAnalyzer()
    analyzer.run()

if __name__ == "__main__":
    main()
