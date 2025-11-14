import os
import shutil
from pathlib import Path

from src.ConsentManager import ConsentManager
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer

def main():
    """
    Main application entry point. Manages user consent, input, and orchestrates
    the analysis and document scraping of a provided zip archive.
    """
    consent = ConsentManager()

    # Reset for testing if needed, uncomment two lines below
    from src.ConfigManager import ConfigManager
    ConfigManager().delete("user_consent")

    if not consent.require_consent():
        print("Consent not given. Exiting program")
        return
    
    analyzer = ProjectAnalyzer()
    analyzer.run()
    

if __name__ == "__main__":
    main()
