import os
from src.ConsentManager import ConsentManager
from src.ZipParser import parse, extract_zip
from src.analyzers.language_detector import analyze_language_share
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from pathlib import Path

def main():
    consent = ConsentManager()

    # Uncomment two lines below to reset consent for testing manually
    from src.ConfigManager import ConfigManager
    ConfigManager().delete("user_consent")

    if not consent.require_consent():
        print("Consent not given. Exiting program.")
        return

    print("Consent confirmed. The application will now proceed.")

    # Enter file path, need full path. Example from my testing: /Users/admin/Desktop/3rdyear.zip
    while True:
        zip_path = input("Please enter the path to the zip file you want to analyze: ").strip()
        zip_path = zip_path.strip("'\"")
        path_obj = Path(zip_path).expanduser()
        if path_obj.exists() and path_obj.suffix.lower() == '.zip':
            zip_path = str(path_obj)
            break
        print("The provided path is invalid or the file is not a .zip file. Please try again.")

    analyzer = GitRepoAnalyzer()
    analyzer.analyze_zip(zip_path)

    print("\nProgram finished.")


    print(f"\nparsing project from: {zip_path}")
    try:
        root_folder = parse(zip_path)
    except Exception as e:
        print(f"Error while parsing: {e}")
        return

    print("\nExtracting project metadata\n")

    metadata_extractor = ProjectMetadataExtractor(root_folder)
    metadata_extractor.extract_metadata()

    print("\nextraction is complete!")


    try:
        root_folder_path = extract_zip(zip_path)
    except Exception as e:
        print(f"Error while extracting: {e}")
        return

    d = analyze_language_share(root_folder_path)
    for language, percentage in d.items():
        print(f"{language}: {percentage}%")

if __name__ == "__main__":
    main()
