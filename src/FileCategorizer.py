import yaml
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any
import os, re

CONFIG_DIR = Path(__file__).parent / "config"
LANG_FILE = CONFIG_DIR / "languages.yml"
MARKUP_FILE = CONFIG_DIR / "markup_languages.yml"
CATEGORIES_FILE = CONFIG_DIR / "categories.yml"
IGNORED_FILE = CONFIG_DIR / "ignored_directories.yml"


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
        self.no_ext_rules = load_yaml(CATEGORIES_FILE).get("no_extension_rules", {})

        #IGNORED directories/extensions/files loaded:
        ignored_data = load_yaml(IGNORED_FILE)
        self.ignored_dirs = set(ignored_data.get("ignored_dirs", []))
        self.ignored_exts = set(ignored_data.get("ignored_extensions", []))
        self.ignored_filenames = set(f.lower() for f in ignored_data.get("ignored_filenames", []))

        #Building extension -> Language maps
        self.language_map = self._build_language_map(self.languages_yaml)
        self.markup_map = self._build_language_map(self.markup_yaml)

        #Extending 'language_source' into real lists
        self.categories = self._expand_category_sources(self.categories_yaml)

    def _build_language_map(self, lang_dict: Dict[str, dict]) -> Dict[str, str]:
        """converts language -> extensions dict into extension-> language"""
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
    
    def _should_ignore(self, path: str) -> bool:
        """Checks if path contains any of the ignored directories or ignored extensions"""
        path_obj = Path(path)
        parts = set(path_obj.parts)
        ext = path_obj.suffix.lstrip(".").lower()
        filename = path_obj.name.lower()

        if not self.ignored_dirs.isdisjoint(parts):
            return True
        if ext in self.ignored_exts:
            return True
        if filename in self.ignored_filenames:
            return True
        
        return False
    
    def _classify_no_extension(self, path: str) -> str:
        """Classify files with no extension based on YAML-defined name patterns."""
        name = Path(path).name.lower()
        for category, conf in self.no_ext_rules.items():
            for key in conf.get("filenames", []):
                if key in name:
                    return category
        # fallback: short filenames look like docs, long ones → other
        if len(name) < 20:
            return "docs"
        # Medium-length lowercase names → probably scripts/configs
        elif len(name) < 40 and name.islower():
            return "config"
        # Otherwise treat as binary/artifact
        else:
            return "binary"
        
    def _split_camel(self, name: str) -> List[str]:
        return re.sub('([a-z])([A-Z])', r'\1 \2', name).lower().split()

    def classify_file(self, file_info: Dict[str, Any]) -> str:
        """Determines category based on path, extension, or language
        file_info format: {'path}: str, 'language': str}
        """
        path = file_info["path"]

        if self._should_ignore(path):
            return "ignored"

        ext = Path(path).suffix.lstrip(".").lower()
        filename = Path(path).name.lower()

        # Infer language if missing
        lang = file_info.get("language")
        if not lang or lang == "Unknown":
            lang = self.language_map.get(ext) or self.markup_map.get(ext)


        # Split filename on non-alphanumeric characters to isolate words
        name_parts = re.split(r'[^a-zA-Z0-9]+', filename)
        camel_parts = self._split_camel(Path(path).stem)
        all_parts = set(name_parts + camel_parts)

        # 1. "test" or "tests" appears as its own word
        if "test" in name_parts or "tests" in name_parts:
            return "test"

        # 2. Filename starts with test_
        if filename.startswith("test_"):
            return "test"

        # 3. Filename ends with _test.<ext>
        if filename.endswith(f"_test.{ext}"):
            return "test"

        # 4. Contains .test., .spec., .fixture.
        if ".test." in filename or ".spec." in filename or ".fixture." in filename:
            return "test"


        # Match by YML-defined categories
        for category, conf in self.categories.items():
            if "path_patterns" in conf and self._match_path_patterns(path, conf["path_patterns"]):
                return category
            if "languages" in conf and lang in conf["languages"]:
                return category
            if "extensions" in conf and ext in [e.lower() for e in conf["extensions"]]:
                return category
            if "filenames" in conf:
                lowered = filename.lower()
                for key in conf["filenames"]:
                    if key.lower() in lowered:
                        return category

        # Handle files without extensions
        if not ext:
            return self._classify_no_extension(path)

        return "other"
    
    def compute_metrics(self, files: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """This classifies the files and computes the count/percent metrics"""
        categories = [self.classify_file(f) for f in files]
        counts = Counter(categories)
        total = sum(counts.values()) or 1

        percentages = {
            cat: round((count / total) * 100, 2)
            for cat, count in counts.items()
        }

        return {"counts": dict(counts), "percentages": percentages}