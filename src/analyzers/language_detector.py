from pathlib import Path
import yaml
from typing import Dict, List, Optional

"""
language_detector.py

The language detector detects each language used in a project
and calculates the share of the project programmed in that language.

The main entry point of the language detector is the analyze_language_share function: 

- This function accepts the path to the root directory of (1) project at a time, as a string.
- Returns a dict:
- Key: the name of the language as a string.
- Value: the share of the project programmed in that language, as a percentage.

E.g. {"Javascript": 48.6, "Java": 43.6, "CSS": 5.9, "SQL": 1.5, "HTML": 0.3}

Workflow overview: 
1. analyze_language_share: acts as the main entry point of the module
2. filter_files: all files are scanned recursively, irrelevant files (e.g. build files, hidden files) are filtered out.
3. aggregate_loc_by_language: for each 'relevant file', if the extension exists in the LANGUAGE_MAP, calls count_loc_by_file helper function.
4. count_loc_by_file: counts lines of code of a file, skipping over empty lines.
5. the final calculation of share per language is done in analyze_language_share, which returns the dict.

Current Limitations:
- does not currently work on non UTF-8 encoded files. 
- currently does not filter out comments when counting lines of code.
- does not currently recognize markup languages (aside from CSS and HTML, which are both in markup_languages.yml and languages.yml for now)
"""


CONFIG_DIR = Path(__file__).parent.parent / "config"
LANGUAGES_FILE = CONFIG_DIR / "languages.yml"
IGNORED_DIRS_FILE = CONFIG_DIR / "ignored_directories.yml"

with open(LANGUAGES_FILE, "r") as f:
    LANGUAGES_YAML = yaml.safe_load(f)

with open(IGNORED_DIRS_FILE, "r") as f:
    IGNORED_DIRS_YAML = yaml.safe_load(f)

# LANGUAGES is a dict of dicts. key = language names, values = dict of each category languages store
#  e.g. {"Python": {"extensions": ["py", "pyw"]}, "Java": {"extensions": ["java", "jsp", "class", "jar"]}}

LANGUAGES = LANGUAGES_YAML["languages"]

# maps extension as key, language as value

LANGUAGE_MAP = {}
for language, category in LANGUAGES.items():
    for extension in category.get("extensions", []):
        LANGUAGE_MAP[extension.lower()] = language

# ignored_directories is split 3-ways into directories, extensions and filenames

IGNORED_DIRS = set(IGNORED_DIRS_YAML.get("ignored_dirs", []))
IGNORED_EXTENSIONS = set(str(ext).lower() for ext in IGNORED_DIRS_YAML.get("ignored_extensions", []))
IGNORED_FILENAMES = set(name.lower() for name in IGNORED_DIRS_YAML.get("ignored_filenames", []))

def analyze_language_share(root_dir: str) -> Dict[str, float]:
    """Return a dict where:
    - Key: language name (str)
    - Value: share of project in that language as a percentage (float)

    E.g. {"Javascript": 48.6, "Java": 43.6, "CSS": 5.9, "SQL": 1.5, "HTML": 0.3}"""
    path = Path(root_dir)
    relevant_files = filter_files(path)
    # calculate lines of code by language
    loc_per_language = aggregate_loc_by_language(relevant_files)
    total_loc_count = sum(loc_per_language.values())
    if total_loc_count == 0:
        return {}
    # calculate the share of each language
    for language in loc_per_language:
        loc_per_language[language] = round((loc_per_language[language] / total_loc_count) * 100, 1)
    return dict(sorted(loc_per_language.items(), key=lambda x: x[1], reverse=True))

def filter_files(path: Path) -> List[Path]:
    """Return a list of files to analyze, ignoring hidden files and specified directories."""
    relevant_files = []
    all_files = [f for f in path.rglob("*") if f.is_file()]

    for file in all_files:
        filename = file.name.lower()
        extension = file.suffix.lstrip(".").lower()

        # 1. Ignore hidden files
        if filename.startswith("."):
            continue

        # 2. Only process known-language extensions
        if extension not in LANGUAGE_MAP:
            continue

        # 3. Ignore extensions
        if extension in IGNORED_EXTENSIONS:
            continue

        # 4. Ignore filenames
        if filename in IGNORED_FILENAMES:
            continue

         # 5. Ignore directories
        if any(part.lower() in IGNORED_DIRS for part in file.parts):
            continue

        relevant_files.append(file)

    return relevant_files

def aggregate_loc_by_language(files: List[Path]) -> Dict[str, int]:
    """Aggregate lines of code per language from a list of files."""
    loc_per_language = {}
    for file in files:
        language = detect_language_per_file(file)
        if not language:
            continue
        loc = count_loc_per_file(file, language)
        if loc is None:
            continue
        loc_per_language[language] = loc_per_language.get(language, 0) + loc
    return loc_per_language

def count_loc_per_file(file: Path, language: str) -> Optional[int]:
    """Count non-empty lines of code in a single file (UTF-8 only)."""
    # Decodes bytes into text using utf-8 encoding. If that's the wrong encoding the file is skipped.
    try:
        with file.open("r", encoding="utf-8", errors="ignore") as f:
            # Generator expression, adds 1 to the sum as it goes through the file line by line, skipping blank lines.
            return sum(1 for line in f if line.strip())
    except Exception:
        return None
    
def detect_language_per_file(file: Path) -> Optional[str]:
    """Return the programming language of a file based on its extension, or None if unknown."""
    extension = file.suffix.lstrip(".").lower()
    return LANGUAGE_MAP.get(extension, None)
    




