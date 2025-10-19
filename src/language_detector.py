from pathlib import Path

LANGUAGE_MAP = {
    'py': 'Python',
    'js': 'JavaScript',
    'ts': 'TypeScript',
    'java': 'Java',
    'rb': 'Ruby',
    'go': 'Go',
    'cs': 'C#',
    'c': 'C',
    'cpp': 'C++',
    'php': 'PHP',
    'rs': 'Rust',
    'kt': 'Kotlin',
    'sh': 'Shell',
    'r': 'R',
    'scala': 'Scala',
}

def is_source_file(path):
    """Check if a path object points to a valid, non-hidden file (by name only)."""
    if not path.name or path.name.startswith('.') or not path.suffix:
        return False
    return True

def get_file_extension(path):
    """Extract the file extension from a path object."""
    if not is_source_file(path):
        return ""
    return path.suffix.lstrip(".").lower()

def find_first_valid_extension(files):
    """Find the extension of the first supported file in a list of files."""
    for file in files:
        path = Path(file)
        if is_source_file(path):
            return get_file_extension(path)
    return None

def detect_language(project_files, language_map=LANGUAGE_MAP):
    """Detect the programming language of a project based on file extensions."""
    ext = find_first_valid_extension(project_files)
    return language_map.get(ext, "Unknown") if ext else "Unknown"
