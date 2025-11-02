import os
import PyPDF2
import docx

class UnsupportedFileType(Exception):
    """Custom exception for unsupported file types."""
    pass

def extract_text_from_txt(file_path):
    """
    Extracts all text from a UTF-8 encoded plain text file (.txt).
    Ref: https://docs.python.org/3/library/functions.html#open
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def extract_text_from_pdf(file_path):
    """
    Extracts all text from a PDF file (.pdf).
    Ref: https://pypdf2.readthedocs.io/en/latest/user/extract-text.html
    """
    text = ""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            if reader.is_encrypted:
                reader.decrypt('') # Attempt decryption with a blank password
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
    except PyPDF2.errors.PdfReadError as e:
        print(f"Error reading PDF file {os.path.basename(file_path)}: {e}")
        return "" # Return empty string for corrupted or unreadable PDFs
    return text

def extract_text_from_docx(file_path):
    """
    Extracts all text from a Microsoft Word document (.docx).
    Ref: https://python-docx.readthedocs.io/en/latest/
    """
    doc = docx.Document(file_path)
    return "\n".join([paragraph.text for paragraph in doc.paragraphs])

def extract_text(file_path):
    """
    Extracts text from a file by routing to the correct parser based on its extension.

    Args:
        file_path (str): The path to the file.

    Returns:
        str: The extracted text.

    Raises:
        FileNotFoundError: If the file_path does not exist.
        UnsupportedFileType: If the file extension is not .txt, .pdf, or .docx.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The file was not found at: {file_path}")

    _, extension = os.path.splitext(file_path)
    ext_lower = extension.lower()

    if ext_lower == '.txt':
        return extract_text_from_txt(file_path)
    elif ext_lower == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext_lower == '.docx':
        return extract_text_from_docx(file_path)
    else:
        raise UnsupportedFileType(f"Unsupported file type: '{extension}'")
