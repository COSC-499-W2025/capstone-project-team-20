import os
from src.ConsentManager import ConsentManager
from src.ProjectAnalyzer import ProjectAnalyzer

def main():
    """
    Main function to run the project analysis tool.

    It handles user consent, prompts for a zip file path,
    and initiates the analysis process.
    """
    consent = ConsentManager()

    # To reset consent for testing, you can uncomment the following lines:
    # from src.ConfigManager import ConfigManager
    # ConfigManager().delete("user_consent")

    if not consent.require_consent():
        print("Consent not given. Exiting program.")
        return

    print("Consent confirmed. The application will now proceed.")

    while True:
        zip_to_analyze = input("Please enter the path to the zip file you want to analyze: ")
        if os.path.exists(zip_to_analyze) and zip_to_analyze.endswith('.zip'):
            break
        print("The provided path is invalid or the file is not a .zip file. Please try again.")

    analyzer = ProjectAnalyzer()
    analyzer.analyze_zip(zip_to_analyze)

    print("\nProgram finished.")


if __name__ == "__main__":
    main()
