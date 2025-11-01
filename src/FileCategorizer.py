import yaml
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any

from src.analyzers.language_detector import LANGUAGE_MAP, MARKUP_LANGUAGE_MAP

CONFIG_DIR = Path(__file__).parent / "config"
LANG_FILE = CONFIG_DIR / "languages.yml"
MARKUP_FILE = CONFIG_DIR / "markup_languages.yml"
CATEGORIES_FILE = CONFIG_DIR / "categories.yml"


def load_yaml(path: Path) -> dict:
    """Helper function for safely loading yaml"""
    with open(path, "r") as f:
        return yaml.safe_load(f)
    

    """
    File: FileCategorizer.py

    The FileCategorizer classifies files into categories such as code, documentation, design, and tests.
    It uses three YAML configuration files (in the config folder) — `languages.yml`, `markup_languages.yml`, and `categories.yml` — 
    to determine how files should be categorized based on their path, file extension, or detected language.

    It is the primary class responsible for categorizing files and computing project-level file metrics.

    Core functionality:
    - YAML Loading: Loads mappings of programming and markup languages, as well as file category definitions.
    - Classification (`classify_file`): Determines the category of a file by checking its path, extension, or language.
    - Metrics Computation (`compute_metrics`): Classifies a list of files and computes counts and percentages per category.

    Example output:
    ```python
    {
        "counts": {"code": 50, "docs": 50, "design": 25, "tests": 25},
        "percentages": {"code": 33.3, "docs": 33.3, "design": 16.67, "tests": 16.67}
    }"""

class FileCategorizer:
    """Classifies files into categories (code, test, docs, design) using categories.ym, languages.yml, markup_languages.yml"""

    def __init__(self):
        #Loading YAML configs
        self.languages_yaml = load_yaml(LANG_FILE)["languages"]
        self.markup_yaml = load_yaml(MARKUP_FILE)["markup_languages"]
        self.categories_yaml = load_yaml(CATEGORIES_FILE)["categories"]

        #Building extension -> Language maps
        self.language_map = self._build_language_map(self.languages_yaml)
        self.markup_map = self._build_language_map(self.markup_yaml)

        #Extending 'language_source' into real lists
        self.categories = self._expand_category_sources(self.categories_yaml)

    def _build_language_map(self, lang_dict: Dict[str, dict]) -> Dict[str, str]:
        """language -> extensions dict into extension-> language"""
        mapping = {}
        for lang, conf in lang_dict.items():
            for ext in conf.get("extensions", []):
                mapping[ext.lower()] = lang
        return mapping
    
    def _expand_category_sources(self, categories: Dict[str, dict]) -> Dict[str, dict]:
        """Resolves any 'language_source' references (e.g 'languages', 'markup_languages', 'all')"""
        expanded = {}
        for cat, conf in categories.items():
            conf = conf.copy()
            src = conf.get("language_source")

            if src == "languages":
                conf["languages"] = list(self.languages_yaml.keys())
            elif src == "markup_languages":
                conf["languages"] = list(self.markup_yaml.keys())
            elif src == "all":
                conf["languages"] = list(self.languages_yaml.keys()) + list(self.markup_yaml.keys())

            expanded[cat] = conf
        return expanded

    def _match_path_patterns(self, path: str, patterns: List[str]) -> bool:
        path = path.lower()
        return any(p.lower() in path for p in patterns)
    
    def classify_file(self, file_info: Dict[str, Any]) -> str:
        """Determines category based on path, extension, or language
        file_info format: {'path}: str, 'language': str}
        """

        path = file_info["path"]
        ext = Path(path).suffix.lstrip(".").lower()
        lang = file_info.get("language", "Unknown")

        for category, conf in self.categories.items():

            # Match by the path patterns
            if "path_patterns" in conf and self._match_path_patterns(path, conf["path_patterns"]):
                return category
            #Match by file extension
            if "extensions" in conf and ext in conf["extensions"]:
                return category
            # Match by language
            if "languages" in conf and lang in conf["languages"]:
                return category
        # default fallback if no match
        return "code"
    
    def compute_metrics(self, files: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """This classifies the files and computes the count/percent metrics"""
        categories = [self.classify_file(f) for f in files]
        counts = Counter(categories)
        total = sum(counts.values()) or 1
        percentages = {cat: round((count / total) * 100, 2) for cat, count in counts.items()}

        return {"counts": dict(counts), "percentages": percentages}