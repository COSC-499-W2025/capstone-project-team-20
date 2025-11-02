import os
import shutil
from src.ConsentManager import ConsentManager
from src.ZipParser import parse, extract_zip
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.DocumentScraper import process_directory

def main():
    """
    Main application entry point. Manages user consent, input, and orchestrates
    the analysis and document scraping of a provided zip archive.
    """
    consent = ConsentManager()

    # Uncomment two lines below to reset consent for testing manually
    # from src.ConfigManager import ConfigManager
    # ConfigManager().delete("user_consent")

    if not consent.require_consent():
        print("Consent not given. Exiting program.")
        return

    print("Consent confirmed. The application will now proceed.")

    # Enter file path, need full path. Example from my testing: /Users/admin/Desktop/3rdyear.zip
    while True:
        zip_path = input("Please enter the path to the zip file you want to analyze: ").strip()
        if os.path.exists(zip_path) and zip_path.endswith('.zip'):
            break
        print("The provided path is invalid or the file is not a .zip file. Please try again.")

    temp_dir = None
    try:
        #analyzer = GitRepoAnalyzer()
        #analyzer.analyze_zip(zip_path)

        #print(f"\nParsing project from: {zip_path}")
        #root_folder = parse(zip_path)

        #print("\nExtracting project metadata\n")
        #metadata_extractor = ProjectMetadataExtractor(root_folder)
        #metadata_extractor.extract_metadata()
        #print("\nextraction is complete!")

        # Document Scraping
        # Extract the zip to a universal temporary directory
        print("\nExtracting zip archive for document scraping...")
        temp_dir = extract_zip(zip_path)

        # Pass the extracted directory to the DocumentScraper
        scraped_data = process_directory(temp_dir)

        if not scraped_data:
            print("\nNo supported documents (.txt, .pdf, .docx) were found for scraping.")
        else:
            print(f"\nSummary: Aggregated text from {len(scraped_data)} document(s).")
            # The 'scraped_data' dictionary is now available here for any future
            # steps, such as piping its contents to another analysis tool.

    except Exception as e:
        print(f"\nAn unexpected error occurred during the process: {e}")
    finally:
        # Ensure the temporary directory is always removed, even if errors occur.
        if temp_dir and os.path.exists(temp_dir):
            print(f"\nCleaning up temporary directory: {temp_dir}")
            # The shutil.rmtree function recursively deletes a directory.
            # Ref: https://docs.python.org/3/library/shutil.html#shutil.rmtree
            shutil.rmtree(temp_dir)

        print("\nProgram finished.")

if __name__ == "__main__":
    main()
