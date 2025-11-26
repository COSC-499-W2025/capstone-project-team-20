import yaml
from pathlib import Path
from collections import Counter
from typing import List, Dict, Any

import os, re

from src.ZipParser import IGNORED_DIRS, IGNORED_EXTS, IGNORED_FILES

CONFIG_DIR = Path(__file__).parent / "config"
LANG_FILE = CONFIG_DIR / "languages.yml"
MARKUP_FILE = CONFIG_DIR / "markup_languages.yml"
CATEGORIES_FILE = CONFIG_DIR / "categories.yml"


def load_yaml(path: Path) -> dict:
    """Helper function for safely loading yaml."""
    with open(path, "r", encoding="utf-8") as f:
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
"""


class FileCategorizer:
    """Classifies files into categories (code, test, docs, design) using
    categories.yml, languages.yml, and markup_languages.yml.
    """

    def __init__(self):
        # Loading YAML configs
        categories_all = load_yaml(CATEGORIES_FILE)
        self.languages_yaml = load_yaml(LANG_FILE)["languages"]
        self.markup_yaml = load_yaml(MARKUP_FILE)["markup_languages"]
        self.categories_yaml = categories_all["categories"]
        self.no_ext_rules = categories_all.get("no_extension_rules", {})

        # IGNORED directories/extensions/files loaded via shared ZipParser config.
        # We don't load ignored_directories.yml here to avoid duplication; instead
        # we import the IGNORED_* sets from src.ZipParser.
        # Building extension -> Language maps
        self.language_map = self._build_language_map(self.languages_yaml)
        self.markup_map = self._build_language_map(self.markup_yaml)

        # Extending 'language_source' into real lists
        self.categories = self._expand_category_sources(self.categories_yaml)

    # ------------------------------------------------------------------
    # Ignore helpers
    # ----------------------------------------------------------------------

    def is_ignored_dir(self, rel_path: Path) -> bool:
        """
        Public helper used by analyzers to decide if a directory should be pruned.

        Delegates to _should_ignore so all ignore logic (dirs/exts/filenames)
        stays centralized and YAML-driven.
        """
        return self._should_ignore(str(rel_path))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_language_map(self, lang_dict: Dict[str, dict]) -> Dict[str, str]:
        """Converts language -> extensions dict into extension -> language."""
        mapping: Dict[str, str] = {}
        for lang, conf in lang_dict.items():
            for ext in conf.get("extensions", []):
                mapping[ext.lower()] = lang
        return mapping

    def _expand_category_sources(self, categories: Dict[str, dict]) -> Dict[str, dict]:
        """Resolves any 'language_source' references (e.g. 'languages', 'markup_languages', 'all')."""
        expanded: Dict[str, dict] = {}
        for cat, conf in categories.items():
            conf = conf.copy()
            src = conf.get("language_source")

            if src == "languages":
                conf["languages"] = list(self.languages_yaml.keys())
            elif src == "markup_languages":
                conf["languages"] = list(self.markup_yaml.keys())
            elif src == "all":
                conf["languages"] = list(self.languages_yaml.keys()) + list(
                    self.markup_yaml.keys()
                )

            expanded[cat] = conf
        return expanded

    def _match_path_patterns(self, path: str, patterns: List[str]) -> bool:
        path_l = path.lower()
        return any(p.lower() in path_l for p in patterns)

    def _should_ignore(self, path: str) -> bool:
        """Checks if path contains any of the ignored directories or ignored extensions/filenames."""
        path_obj = Path(path)
        parts = set(path_obj.parts)
        ext = path_obj.suffix.lstrip(".").lower()
        filename = path_obj.name.lower()

        if not IGNORED_DIRS.isdisjoint(parts):
            return True
        if ext in IGNORED_EXTS:
            return True
        if filename in IGNORED_FILES:
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
        if name.islower() and len(name) < 50:
            return "config"
        return "other"

    def _split_camel(self, name: str) -> List[str]:
        """Split camelCase / PascalCase into component words."""
        return re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)", name)

    # ------------------------------------------------------------------
    # Public classification API
    # ------------------------------------------------------------------

    def classify_file(self, file_info: Dict[str, Any]) -> str:
        """
        Classify a file into one of the configured categories.

        file_info:
          {
            "path": "relative/path/to/file.ext",
            "language": "Python" | "JavaScript" | ...
          }
        """
        path = file_info.get("path", "")
        lang = (file_info.get("language") or "").strip()
        ext = Path(path).suffix.lower().lstrip(".")

        # First, ignore if it matches ignored dirs/exts/filenames
        if self._should_ignore(path):
            return "ignored"

        # No extension? Use name-based rules.
        if not ext:
            return self._classify_no_extension(path)

        # Explicit test classification heuristics
        test_cat = self._classify_test_like(path, lang, ext)
        if test_cat == "test":
            return "test"

        # Match by YML-defined categories
        for category, conf in self.categories.items():
            if "path_patterns" in conf and self._match_path_patterns(
                path, conf["path_patterns"]
            ):
                return category
            if "languages" in conf and lang in conf["languages"]:
                return category
            if "extensions" in conf and ext in [e.lower() for e in conf["extensions"]]:
                return category

        # Fallback heuristics
        lower_path = path.lower()
        if any(x in lower_path for x in ("readme", "docs/", "documentation")):
            return "docs"
        if any(x in lower_path for x in ("design", "uml", "diagram")):
            return "design"

        return "code" if lang else "other"

    def _classify_test_like(self, path: str, lang: str, ext: str) -> str:
        """
        Heuristics for test files, based on filename patterns and language.

        Examples:
          - tests/ or test/ directories
          - filenames containing test, spec, fixture
        """
        path_l = path.lower()
        filename = Path(path).name.lower()

        # Directory based
        if "/tests/" in path_l or "/test/" in path_l:
            return "test"

        # For JS / TS: __tests__ folders
        if "__tests__" in path_l:
            return "test"

        # Name-based patterns
        name_parts = re.split(r"[^a-zA-Z0-9]+", filename)
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

        # 5. For pytest-style tests: test-*.py
        if lang.lower() == "python" and filename.startswith("test-"):
            return "test"

        return "other"

    # ------------------------------------------------------------------
    # Metrics API
    # ------------------------------------------------------------------

    def compute_metrics(self, files: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """Classifies the files and computes the count/percent metrics."""
        categories = [self.classify_file(f) for f in files]
        counts = Counter(categories)
        total = sum(counts.values()) or 1

        percentages = {
            cat: round((count / total) * 100, 2) for cat, count in counts.items()
        }

        return {"counts": dict(counts), "percentages": percentages}
