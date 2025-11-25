from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Iterable, Set

import os
import re

from src.FileCategorizer import FileCategorizer
from .language_detector import detect_language_per_file


@dataclass
class CodeFileAnalysis:
    """
    Per-file metrics for code/test files within a project.
    """

    path: Path
    language: Optional[str]
    is_test: bool

    total_lines: int
    code_lines: int
    comment_lines: int
    blank_lines: int

    function_count: int
    max_function_length: int

    # Skills hinted by snippet patterns (filled later by SkillAnalyzer)
    snippet_skills: List[str] = field(default_factory=list)


class CodeMetricsAnalyzer:
    """
    Walks an extracted project directory and computes code metrics for
    all files categorized as 'code' or 'tests' by FileCategorizer.
    """

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)
        self.categorizer = FileCategorizer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self) -> List[CodeFileAnalysis]:
        """
        Perform code-metrics analysis for all code/test files.

        Returns:
            A list of CodeFileAnalysis objects, one per analyzed file.
        """
        analyses: List[CodeFileAnalysis] = []
        seen_paths: Set[Path] = set()

        for file_path in self._iter_candidate_files():
            # Extra safety: avoid duplicate processing of the same file
            file_path = file_path.resolve()
            if file_path in seen_paths:
                continue
            seen_paths.add(file_path)

            rel_path = file_path.relative_to(self.root_dir)
            language = detect_language_per_file(file_path)
            file_info = {"path": str(rel_path), "language": language or "Unknown"}

            category = self.categorizer.classify_file(file_info)
            if category in ("ignored", None):
                continue

            is_test = self._is_test_file(rel_path, category)
            if category not in ("code", "tests"):
                # Analysis is only done in code/test files.
                continue

            analysis = self._analyze_single_file(file_path, language, is_test)
            analyses.append(analysis)

        return analyses

    def summarize(self, analyses: List[CodeFileAnalysis]) -> Dict[str, Any]:
        """
        Aggregate per-file metrics into project-level statistics.

        Returns:
            A dictionary with overall and per-language summaries.
        """
        if not analyses:
            return {
                "overall": {},
                "per_language": {},
            }

        overall: Dict[str, Any] = {}
        per_language: Dict[str, Dict[str, Any]] = {}

        total_files = len(analyses)
        total_loc = 0
        total_comment = 0
        total_blank = 0
        total_functions = 0
        max_function_len = 0
        num_test_files = 0
        num_code_files = 0

        for a in analyses:
            lang = a.language or "Unknown"
            if lang not in per_language:
                per_language[lang] = {
                    "files": 0,
                    "loc": 0,
                    "comment_lines": 0,
                    "blank_lines": 0,
                    "functions": 0,
                    "max_function_length": 0,
                }

            lang_entry = per_language[lang]
            lang_entry["files"] += 1
            lang_entry["loc"] += a.code_lines
            lang_entry["comment_lines"] += a.comment_lines
            lang_entry["blank_lines"] += a.blank_lines
            lang_entry["functions"] += a.function_count
            lang_entry["max_function_length"] = max(
                lang_entry["max_function_length"], a.max_function_length
            )

            total_loc += a.code_lines
            total_comment += a.comment_lines
            total_blank += a.blank_lines
            total_functions += a.function_count
            max_function_len = max(max_function_len, a.max_function_length)

            if a.is_test:
                num_test_files += 1
            else:
                num_code_files += 1

        avg_functions_per_file = total_functions / total_files if total_files else 0.0
        comment_ratio = (
            total_comment / (total_comment + total_loc)
            if (total_comment + total_loc) > 0
            else 0.0
        )
        test_file_ratio = num_test_files / (num_code_files or 1)

        overall.update(
            {
                "total_files": total_files,
                "total_loc": total_loc,
                "total_comment_lines": total_comment,
                "total_blank_lines": total_blank,
                "avg_functions_per_file": round(avg_functions_per_file, 2),
                "max_function_length": max_function_len,
                "comment_ratio": round(comment_ratio, 3),
                "num_test_files": num_test_files,
                "num_code_files": num_code_files,
                "test_file_ratio": round(test_file_ratio, 3),
            }
        )

        # add derived language-level ratios
        for lang, data in per_language.items():
            loc = data["loc"]
            cmt = data["comment_lines"]
            data["comment_ratio"] = cmt / (cmt + loc) if (cmt + loc) > 0 else 0.0
            data["avg_functions_per_file"] = (
                data["functions"] / data["files"] if data["files"] else 0.0
            )

        return {
            "overall": overall,
            "per_language": per_language,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _iter_candidate_files(self) -> Iterable[Path]:
        """
        Iterate over all regular files under root_dir, pruning ignored directories
        and files based on ignored_directories.yml via FileCategorizer.
        """
        root_str = str(self.root_dir)

        for root, dirs, files in os.walk(root_str):
            root_path = Path(root)
            rel_root = root_path.relative_to(self.root_dir)

            # 1) Prune dirs using FileCategorizer + ignored_directories.yml
            dirs[:] = [
                d
                for d in dirs
                if not self.categorizer.is_ignored_dir(rel_root / d)
            ]

            # 2) Yield files that are not ignored by FileCategorizer
            for fname in files:
                file_path = root_path / fname
                rel = file_path.relative_to(self.root_dir)

                # Reuse FileCategorizer's ignore logic for files
                if hasattr(self.categorizer, "_should_ignore") and self.categorizer._should_ignore(
                    str(rel)
                ):
                    continue

                yield file_path

    def _analyze_single_file(
        self, file_path: Path, language: Optional[str], is_test: bool
    ) -> CodeFileAnalysis:
        """
        Compute metrics for a single file.
        """
        total = 0
        code = 0
        comment = 0
        blank = 0

        function_count = 0
        max_func_len = 0
        current_func_len = 0
        in_function = False

        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            # If unreadable, return an empty analysis
            return CodeFileAnalysis(
                path=file_path,
                language=language,
                is_test=is_test,
                total_lines=0,
                code_lines=0,
                comment_lines=0,
                blank_lines=0,
                function_count=0,
                max_function_length=0,
            )

        for line in text.splitlines():
            total += 1
            stripped = line.strip()

            if not stripped:
                blank += 1
                if in_function:
                    current_func_len += 1
                continue

            if self._is_comment_line(stripped, language):
                comment += 1
                if in_function:
                    current_func_len += 1
                continue

            # It's code
            code += 1
            if self._looks_like_function_def(stripped, language):
                # Close previous function block
                if in_function:
                    max_func_len = max(max_func_len, current_func_len)
                in_function = True
                function_count += 1
                current_func_len = 1
            elif in_function:
                current_func_len += 1

        if in_function:
            max_func_len = max(max_func_len, current_func_len)

        return CodeFileAnalysis(
            path=file_path,
            language=language,
            is_test=is_test,
            total_lines=total,
            code_lines=code,
            comment_lines=comment,
            blank_lines=blank,
            function_count=function_count,
            max_function_length=max_func_len,
        )

    # Very lightweight heuristics.

    def _is_comment_line(self, stripped: str, language: Optional[str]) -> bool:
        lang = (language or "").lower()

        if stripped.startswith("#"):
            # Python, shell, etc.
            return True

        if stripped.startswith("//"):
            # C-like single-line comment
            return True

        if stripped.startswith("/*") or stripped.startswith("*") or stripped.startswith(
            "*/"
        ):
            return True

        # Python docstrings as comments
        if lang == "python" and (
            stripped.startswith('"""') or stripped.startswith("'''")
        ):
            return True

        return False

    def _is_test_file(self, rel_path: Path, category: Optional[str]) -> bool:
        """
        Heuristic to decide whether a file should be treated as a test file.

        We combine:
          - FileCategorizer category (if it explicitly says "tests"/"test"),
          - Common path/name patterns: tests/, test_*.py, *_test.py, etc.
        """
        if category in ("tests", "test"):
            return True

        # Normalize parts and name for path-based heuristics
        parts = [p.lower() for p in rel_path.parts]
        name = rel_path.name.lower()

        # Typical test directories: tests/, test/, __tests__/, etc.
        if any(part in ("tests", "test", "__tests__") for part in parts):
            return True

        # Typical test filenames: test_foo.py, foo_test.py, *.spec.js, *.test.ts
        if name.startswith("test_") or name.endswith("_test.py"):
            return True
        if name.endswith(".spec.js") or name.endswith(".test.js"):
            return True
        if name.endswith(".spec.ts") or name.endswith(".test.ts"):
            return True

        return False

    def _looks_like_function_def(self, stripped: str, language: Optional[str]) -> bool:
        lang = (language or "").lower()

        # Python: def foo(...):
        if "python" in lang:
            return bool(re.match(r"^def\s+\w+\s*\(", stripped))

        # JavaScript / TypeScript classic function
        if lang in ("javascript", "typescript"):
            if re.match(r"^(async\s+)?function\s+\w+\s*\(", stripped):
                return True
            # Simple arrow function heuristic: const foo = (...) =>
            if "=>" in stripped and re.search(r"\bfunction\b", stripped) is None:
                return True

        # C / C++ / Java / C#
        if lang in ("c", "c++", "cpp", "java", "c#"):
            # Very naive: "type name(args) {"
            return bool(
                re.match(r"[A-Za-z_][A-Za-z0-9_<>,\s\*]*\([^)]*\)\s*\{", stripped)
            )

        # generic fallback: anything that looks like name(args) {
        return bool(re.match(r"\w+\s*\([^)]*\)\s*\{", stripped))
