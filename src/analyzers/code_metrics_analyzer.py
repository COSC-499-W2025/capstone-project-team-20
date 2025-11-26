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
    Holds metrics for a single file.
    """

    path: Path
    language: Optional[str] = None
    is_test: bool = False

    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    blank_lines: int = 0

    function_count: int = 0
    max_function_length: int = 0

    snippet_matches: Dict[str, int] = field(default_factory=dict)


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
        Walk the project tree and compute per-file metrics.
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
            if category not in ("code", "tests", "test"):
                # Analysis is only done on code or tests.
                continue

            analysis = self._analyze_single_file(file_path, language, is_test)
            analyses.append(analysis)

        return analyses

    def summarize(self, analyses: List[CodeFileAnalysis]) -> Dict[str, Any]:
        """
        Summarize the per-file analyses into overall stats and per-language stats.
        """
        overall = {
            "file_count": len(analyses),
            "total_lines_of_code": sum(a.code_lines for a in analyses),
            "avg_function_length": 0.0,
            "max_function_length": 0,
        }

        total_functions = sum(a.function_count for a in analyses)
        if total_functions > 0:
            overall["avg_function_length"] = (
                sum(a.max_function_length for a in analyses) / total_functions
            )

        overall["max_function_length"] = (
            max((a.max_function_length for a in analyses), default=0)
        )

        # Group by language
        per_language: Dict[str, Dict[str, Any]] = {}
        for a in analyses:
            lang = a.language or "Unknown"
            if lang not in per_language:
                per_language[lang] = {
                    "file_count": 0,
                    "total_lines_of_code": 0,
                    "test_file_count": 0,
                    "max_function_length": 0,
                }
            stats = per_language[lang]
            stats["file_count"] += 1
            stats["total_lines_of_code"] += a.code_lines
            if a.is_test:
                stats["test_file_count"] += 1
            stats["max_function_length"] = max(
                stats["max_function_length"], a.max_function_length
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
            return CodeFileAnalysis(
                path=file_path,
                language=language,
                is_test=is_test,
            )

        lines = text.splitlines()
        total = len(lines)

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank += 1
            elif stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*"):
                comment += 1
            else:
                code += 1

            # Naive function detection
            if self._is_function_start(stripped, language):
                if in_function:
                    # Close previous function
                    max_func_len = max(max_func_len, current_func_len)
                in_function = True
                current_func_len = 1
                function_count += 1
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

    def _is_test_file(self, rel_path: Path, category: str) -> bool:
        """Decide if a file should be treated as test code."""
        if category in ("tests", "test"):
            return True
        lower = str(rel_path).lower()
        return "/tests/" in lower or "/test/" in lower

    def _is_function_start(self, stripped: str, language: Optional[str]) -> bool:
        """
        Rough heuristic to detect when a line starts a function or method.
        This is intentionally simple and language-agnostic.
        """
        if not stripped:
            return False

        lang = (language or "").lower()

        # Python: def foo(
        if lang == "python":
            return stripped.startswith("def ") and "(" in stripped and ":" in stripped

        # JavaScript / TypeScript / C-like:
        if lang in ("javascript", "typescript", "js", "ts"):
            # function foo(
            if stripped.startswith("function "):
                return True
            # foo() {
            if re.match(r"\w+\s*\([^)]*\)\s*\{", stripped):
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
