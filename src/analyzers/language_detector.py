from pathlib import Path
import yaml
from src.Project import Project
from typing import Dict, Optional


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

def run_analysis(root_dir: str) -> Dict[str,int]:
    path = Path(root_dir)
    relevant_files = filter_files(path)
    loc_per_language = aggregate_loc_by_language(relevant_files)
    share_per_language = loc_per_language.copy()
    total_loc_count = sum(loc_per_language.values())
    for language in share_per_language:
        share_per_language[language] = round((loc_per_language[language] / total_loc_count) * 100)
    return share_per_language

def filter_files(path: Path) -> list[Path]:
    relevant_files = []
    all_files = [f for f in path.rglob("*") if f.is_file()]
    for file in all_files:
        if file.name.startswith("."):
            continue
        if file.suffix.lstrip(".").lower() not in LANGUAGE_MAP:
            continue
        relevant_files.append(file)
    return relevant_files

def aggregate_loc_by_language(files: list[Path]) -> Dict[str,int]:
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

def count_loc_per_file(file: Path, language: str) -> int:
    # Decodes bytes into text using utf-8 encoding. If that's the wrong encoding the file is skipped.
    try:
        with file.open("r", encoding="utf-8", errors="ignore") as f:
            # Generator expression, adds 1 to the sum as it goes through the file line by line.
            # Iterating over f automatically yields each line in the file. If line.strip() is not True, the line is blank.
            return sum(1 for line in f if line.strip())
    except Exception:
        return None
    
def detect_language_per_file(file: Path) -> Optional[str]:
    extension = file.suffix.lstrip(".").lower()
    return LANGUAGE_MAP.get(extension, None)




