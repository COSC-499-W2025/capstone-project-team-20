from pathlib import Path
import yaml
from src.Project import Project

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

def Analyze(proj: Project):
    #path = Path(proj.root_dir)
    #Filter(path)
    pass

def Filter(path: Path) -> list[Path]:
    relevant_files = []
    all_files = [f for f in path.rglob("*") if f.is_file()]
    for file in all_files:
        #Filter irrelevant files
        if file.name.startswith("."):
            continue
        if file.suffix.lstrip(".").lower() not in LANGUAGE_MAP:
            continue
        relevant_files.append(file)
    return relevant_files


