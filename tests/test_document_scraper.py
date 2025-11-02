import pytest
import os
import shutil
import sys
import tempfile

# Add project root to Python path to allow imports from 'src' and 'utils'
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.DocumentScraper import scrape_and_display, process_directory
from utils.document_handler import UnsupportedFileType
from docx import Document
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# Constants for Test Data
UNIQUE_TEXT_TXT = "Unique text for the TXT file."
UNIQUE_TEXT_DOCX = "Unique text for the DOCX file."
UNIQUE_TEXT_PDF = "Unique text for the PDF file."

@pytest.fixture(scope="module")
def mock_document_suite():
    """
    Pytest fixture to create a temporary directory populated with a variety
    of mock document files for testing. This fixture has 'module' scope,
    meaning it runs once for all tests in this file, improving efficiency.
    Ref: https://docs.pytest.org/en/6.2.x/fixture.html
    """
    temp_dir = tempfile.mkdtemp(prefix="doc_suite_")

    file_paths = {
        "txt": os.path.join(temp_dir, "test.txt"),
        "docx": os.path.join(temp_dir, "test.docx"),
        "pdf": os.path.join(temp_dir, "test.pdf"),
        "unsupported": os.path.join(temp_dir, "script.jpeg"),
        "empty": os.path.join(temp_dir, "empty.txt"),
    }

    # --- Create Mock Files ---
    with open(file_paths["txt"], "w", encoding="utf-8") as f:
        f.write(UNIQUE_TEXT_TXT)

    doc = Document()
    doc.add_paragraph(UNIQUE_TEXT_DOCX)
    doc.save(file_paths["docx"])

    c = canvas.Canvas(file_paths["pdf"], pagesize=letter)
    c.drawString(72, 800, UNIQUE_TEXT_PDF)
    c.save()

    with open(file_paths["unsupported"], "w") as f:
        f.write("print('hello')")

    with open(file_paths["empty"], "w") as f:
        f.write("")

    # Yield the dictionary of file paths to the test functions
    yield {"dir": temp_dir, "files": file_paths}

    # --- Teardown ---
    shutil.rmtree(temp_dir)

# --- Tests for the helper function: scrape_and_display ---

def test_scrape_and_display_txt(mock_document_suite, capsys):
    """Verify correct scraping and display for .txt files."""
    result = scrape_and_display(mock_document_suite["files"]["txt"])
    captured = capsys.readouterr()
    assert UNIQUE_TEXT_TXT in result
    assert "Snippet from: test.txt" in captured.out

def test_scrape_and_display_docx(mock_document_suite, capsys):
    """Verify correct scraping and display for .docx files."""
    result = scrape_and_display(mock_document_suite["files"]["docx"])
    captured = capsys.readouterr()
    assert UNIQUE_TEXT_DOCX in result
    assert "Snippet from: test.docx" in captured.out

def test_scrape_and_display_pdf(mock_document_suite, capsys):
    """Verify correct scraping and display for .pdf files."""
    result = scrape_and_display(mock_document_suite["files"]["pdf"])
    captured = capsys.readouterr()
    assert UNIQUE_TEXT_PDF in result
    assert "Snippet from: test.pdf" in captured.out

def test_scrape_and_display_unsupported(mock_document_suite):
    """Verify that unsupported file types return an empty string."""
    result = scrape_and_display(mock_document_suite["files"]["unsupported"])
    assert result == ""

def test_scrape_and_display_empty_file(mock_document_suite):
    """Verify that empty files return an empty string."""
    result = scrape_and_display(mock_document_suite["files"]["empty"])
    assert result == ""

# --- Tests for the orchestrator function: process_directory ---

def test_process_directory_aggregation(mock_document_suite):
    """
    Verify that the orchestrator correctly traverses a directory, calls the
    helper, and aggregates the results into a lookup table.
    """
    directory_path = mock_document_suite["dir"]
    result_table = process_directory(directory_path)

    # 1. Check that exactly 3 supported documents were scraped and aggregated
    assert len(result_table) == 3

    # 2. Verify the content for each file in the lookup table
    assert UNIQUE_TEXT_TXT in result_table["test.txt"]
    assert UNIQUE_TEXT_DOCX in result_table["test.docx"]
    assert UNIQUE_TEXT_PDF in result_table["test.pdf"]

    # 3. Ensure unsupported and empty files were not added to the table
    assert "script.py" not in result_table
    assert "empty.txt" not in result_table

def test_process_directory_on_empty_dir():
    """Verify that the orchestrator handles an empty directory gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        result_table = process_directory(temp_dir)
        assert len(result_table) == 0
        assert result_table == {}
