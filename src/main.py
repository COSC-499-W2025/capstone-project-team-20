from src.ConsentManager import ConsentManager
from src.ZipParser import parse
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor

def main():
    consent = ConsentManager()

    # Uncomment two lines below to reset consent for testing manually
    from src.ConfigManager import ConfigManager
    ConfigManager().delete("user_consent") 

    if not consent.require_consent():
        print("Consent not given. Exiting program.")
        return
    
    print("Consent confirmed in main.")

    zip_path = input("Enter the path to the zipped project file: ").strip()
    # Enter file path, need full path. Example from my testing: /Users/admin/Desktop/3rdyear.zip
    

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

if __name__ == "__main__":
    main()