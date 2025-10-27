from pathlib import Path
import yaml

CONFIG_DIR = Path(__file__).parent.parent / "config"
LANGUAGES_FILE = CONFIG_DIR / "languages.yml"
MARKUP_FILE = CONFIG_DIR / "markup_languages.yml"

with open(LANGUAGES_FILE, "r") as f:
    LANGUAGES_YAML = yaml.safe_load(f)

with open(MARKUP_FILE, "r") as f:
    MARKUP_LANGUAGES_YAML = yaml.safe_load(f)

# LANGUAGES is a dict of dicts. key = language names, values = dict of each category languages store
#  e.g. {"Python": {"extensions": ["py", "pyw"]}, "Java": {"extensions": ["java", "jsp", "class", "jar"]}}

LANGUAGES = LANGUAGES_YAML["languages"]
MARKUP_LANGUAGES = MARKUP_LANGUAGES_YAML["markup_languages"]

# maps extension as key, language as value

LANGUAGE_MAP = {}
for language, category in LANGUAGES.items():
    for extension in category.get("extensions", []):
        LANGUAGE_MAP[extension.lower()] = language

MARKUP_LANGUAGE_MAP = {}
for language, category in MARKUP_LANGUAGES.items():
    for extension in category.get("extensions", []):
        MARKUP_LANGUAGE_MAP[extension.lower()] = language

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
    """
    Find the extension of the first supported file in a list of files.
    A valid file is:
    - Not hidden (does not start with a dot)
    - Has a file extension
    Non-programming files such as README.md are valid
    """
    for file in files:
        path = Path(file)
        if is_source_file(path):
            return get_file_extension(path)
    return None

def detect_language(project_files, language_map=LANGUAGE_MAP):
    """
    Detect the programming language of a project based on file extensions.
    Extensions are mapped to languages using the provided language_map.
    """
    ext = find_first_valid_extension(project_files)
    if ext in language_map:
        return language_map[ext]
    return "Unknown"
