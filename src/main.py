import os
from src.ConsentManager import ConsentManager
from src.ProjectAnalyzer import ProjectAnalyzer

def main():
    consent = ConsentManager()

    # Uncomment two lines below to reset consent for testing manually
    from src.ConfigManager import ConfigManager
    ConfigManager().delete("user_consent")

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
