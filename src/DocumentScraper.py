import os
import sys
from typing import Dict

# Add project root to Python path to enable imports from 'utils'
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.document_handler import extract_text, UnsupportedFileType

def scrape_and_display(file_path: str) -> str:
    """
    Scrapes a single document file, displays a formatted snippet of its
    content, and returns the full extracted text. This function is designed
    to be called repeatedly by an orchestrator.

    Args:
        file_path: The absolute path to the document file to be processed.

    Returns:
        The full extracted text as a string, or an empty string if no text
        is found, the file is unsupported, or an error occurs.
    """
    try:
        # Delegate the core extraction logic to the handler in 'utils'
        content = extract_text(file_path)
        if content and content.strip():
            # Display a formatted snippet for immediate user feedback
            print(f"\n--- Snippet from: {os.path.basename(file_path)} ---")
            lines = content.splitlines()
            for i, line in enumerate(lines[:5]):
                print(f"{i+1:2d} | {line}")
            if len(lines) > 5:
                print(f"... and {len(lines) - 5} more lines.")
            print("-------------------------------------------------")
            return content
    except UnsupportedFileType:
        # This is an expected case for non-document files; fail silently.
        return ""
    except Exception as e:
        # Log other errors but do not halt the overall scraping process.
        print(f"  [!] Error processing {os.path.basename(file_path)}: {e}")
        return ""
    return ""

def process_directory(directory_path: str) -> Dict[str, str]:
    """
    Main orchestrator for the document scraping process. It traverses a directory
    tree, calls the scraping helper for each file, and aggregates the results
    into a lookup table.

    This function is intended to be called from main.py after zip extraction.

    Args:
        directory_path: The root path of the directory to be scraped.

    Returns:
        A dictionary where keys are the relative file paths (from the directory
        root) and values are the full extracted text content.
    """
    lookup_table: Dict[str, str] = {}
    print("\n--- Initiating Document Scraping Process ---")

    # The os.walk function provides a systematic way to traverse a directory tree.
    # Ref: https://docs.python.org/3/library/os.html#os.walk
    for root, _, files in os.walk(directory_path):
        for filename in files:
            file_path = os.path.join(root, filename)

            # Call the helper function to process one file and display its snippet
            content = scrape_and_display(file_path)

            # If content was successfully extracted, add it to our aggregate dictionary
            if content:
                relative_path = os.path.relpath(file_path, directory_path)
                lookup_table[relative_path] = content

    print("\n--- Document Scraping Process Complete ---")
    return lookup_table
