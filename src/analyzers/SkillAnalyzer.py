from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Callable, Tuple, Set

import os

from src.FileCategorizer import FileCategorizer

from .skill_models import Evidence, SkillProfileItem, TAXONOMY
from .skill_patterns import DEP_TO_SKILL, SNIPPET_PATTERNS, KNOWN_CONFIG_HINTS
from .skill_proficiency import ProficiencyEstimator
from .code_metrics_analyzer import CodeMetricsAnalyzer, CodeFileAnalysis

# Heuristic mapping: which snippet-based skills make sense for which languages.
# This lets us avoid running JS regexes on Python files, etc.
LANG_TO_ALLOWED_SNIPPET_SKILLS: Dict[str, Set[str]] = {
    "python": {"Django", "Flask", "FastAPI", "Python"},
    "javascript": {"React", "Next.js"},
    "typescript": {"React", "Next.js"},
    "js": {"React", "Next.js"},
    "ts": {"React", "Next.js"},
    "c++": {"C++", "CMake"},
    "cpp": {"C++", "CMake"},
    "c": {"CMake"},
    "c#": {"C#", "CMake"},
    "java": {"Java", "CMake"},
    "rust": {"Rust", "CMake"},
}

DEPENDENCY_FILES = {
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "requirements.txt",
        "pyproject.toml",
        "Pipfile",
        "Pipfile.lock",
        "environment.yml",
        "poetry.lock",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "go.mod",
    }


class SkillAnalyzer:
    """
    High-level skill analysis for a single extracted project directory.

    Responsibilities:
    - Run CodeMetricsAnalyzer to compute per-file metrics
    - Extract Evidence objects from:
      - languages used (via file extensions / language detection),
      - dependencies (requirements.txt, package.json, pom.xml, etc.),
      - config file conventions (Dockerfile, next.config.js, etc.),
      - snippet patterns in code (import lines, includes, etc.).
    - Aggregate Evidence into SkillProfileItem objects with proficiency scores.
    """

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)
        self.metrics_analyzer = CodeMetricsAnalyzer(self.root_dir)
        self.prof_estimator = ProficiencyEstimator()
        # Reuse the same config-driven ignore behaviour as CodeMetricsAnalyzer
        self.categorizer = FileCategorizer()

    # ------------------------------------------------------------------
    # Internal helpers for walking the project tree with ignores
    # ------------------------------------------------------------------

    def _iter_project_files(self) -> Iterable[Path]:
        """
        Walk the project tree, pruning ignored directories and files based on
        FileCategorizer's configuration (including ignored_directories.yml).
        """
        root_str = str(self.root_dir)

        for root, dirs, files in os.walk(root_str):
            root_path = Path(root)
            rel_root = root_path.relative_to(self.root_dir)

            # 1) Prune directories using FileCategorizer + ignored_directories.yml
            dirs[:] = [
                d
                for d in dirs
                if not self.categorizer.is_ignored_dir(rel_root / d)
            ]

            # 2) Yield files that are not ignored by FileCategorizer
            for fname in files:
                file_path = root_path / fname
                rel = file_path.relative_to(self.root_dir)

                if hasattr(self.categorizer, "_should_ignore") and self.categorizer._should_ignore(
                    str(rel)
                ):
                    continue

                yield file_path

    def _iter_pattern_pairs(self, raw_patterns: Iterable[Any]) -> Iterable[tuple[Any, str]]:
        """
        Normalize whatever structure DEP_TO_SKILL / SNIPPET_PATTERNS use into
        (pattern, skill) pairs.
        """
        for item in raw_patterns:
            pattern = None
            skill = None

            if isinstance(item, tuple):
                if len(item) >= 2:
                    pattern, skill = item[0], item[1]
            elif isinstance(item, dict):
                pattern = item.get("pattern")
                skill = item.get("skill")
            else:
                pattern = getattr(item, "pattern", None)
                skill = getattr(item, "skill", None)

            if pattern is None or skill is None:
                continue

            yield pattern, skill

    def _iter_config_hints(
        self, raw_hints: Iterable[Any]
    ) -> Iterable[Tuple[Callable[[str], bool], str, str]]:
        """
        Normalize KNOWN_CONFIG_HINTS into (checker, skill, source_kind) tuples.

        Supports:
          - Tuples: (pattern, skill) or (pattern, skill, source_kind)
          - Dicts: {"pattern": ..., "skill": ..., "source_kind": "..."}
          - Objects with .matches(name), .skill, .source_kind
        """
        for item in raw_hints:
            pattern = None
            skill = None
            source_kind = "config_hint"

            if isinstance(item, tuple):
                if len(item) >= 2:
                    pattern, skill = item[0], item[1]
                if len(item) >= 3:
                    source_kind = item[2]
            elif isinstance(item, dict):
                pattern = item.get("pattern")
                skill = item.get("skill")
                source_kind = item.get("source_kind", source_kind)
            else:
                # object with .matches, .skill, .source_kind
                if hasattr(item, "matches") and hasattr(item, "skill"):
                    def checker(name: str, h=item) -> bool:
                        return h.matches(name)

                    skill = getattr(item, "skill")
                    source_kind = getattr(item, "source_kind", source_kind)
                    yield checker, skill, source_kind
                    continue

            if pattern is None or skill is None:
                continue

            # Build checker from pattern
            if hasattr(pattern, "search"):
                def checker(name: str, p=pattern) -> bool:
                    return bool(p.search(name))
            else:
                pat_str = str(pattern).lower()

                def checker(name: str, s=pat_str) -> bool:
                    return s in name.lower()

            yield checker, skill, source_kind

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def analyze(self) -> Dict[str, Any]:
        """
        Perform full skill analysis.

        Returns:
            {
              "skills": List[SkillProfileItem],
              "stats": Dict[str, Any],   # project-level metrics used for scoring
              "dimensions": Dict[str, Any],
              "resume_suggestions": List[Dict[str, Any]],
            }
        """
        file_analyses = self.metrics_analyzer.analyze()
        stats = self._build_stats(file_analyses)

        self._extract_snippet_skills(file_analyses)

        evidence: List[Evidence] = []
        evidence.extend(self._language_evidence(file_analyses))
        evidence.extend(self._dependency_evidence())
        evidence.extend(self._config_evidence())
        evidence.extend(self._snippet_evidence(file_analyses))

        skills = self._build_skill_profiles(evidence, stats)
        dimensions = self._compute_dimensions(stats)

        # placeholder for future fully-formed bullets
        resume_suggestions: List[Dict[str, Any]] = []

        return {
            "skills": skills,
            "stats": stats,
            "dimensions": dimensions,
            "resume_suggestions": resume_suggestions,
        }

    # ------------------------------------------------------------------
    # Stats used by ProficiencyEstimator / dimensions
    # ------------------------------------------------------------------

    def _build_stats(self, file_analyses: List[CodeFileAnalysis]) -> Dict[str, Any]:
        """
        Produce a stats dict from code metrics.
        """
        summary = self.metrics_analyzer.summarize(file_analyses)
        overall = summary.get("overall", {})
        per_lang = summary.get("per_language", {})

        stats: Dict[str, Any] = {
            "overall": overall,
            "per_language": per_lang,
        }

        # Provide a Python-specific section if Python files exist
        py_key = None
        for lang_name in per_lang.keys():
            if lang_name and lang_name.lower().startswith("python"):
                py_key = lang_name
                break

        if py_key:
            py_data = per_lang[py_key]
            stats["python"] = {
                "files": py_data.get("file_count", 0),
                "loc": py_data.get("loc", 0),
                "functions": py_data.get("functions", 0),
                "comment_ratio": py_data.get("comment_ratio", 0.0),
                "avg_functions_per_file": py_data.get("avg_functions_per_file", 0.0),
            }

        # Could add similar language-specific blocks for JS/TS, C++, etc. later
        return stats

    # ------------------------------------------------------------------
    # Evidence extraction
    # ------------------------------------------------------------------

    def _language_evidence(
        self, file_analyses: Iterable[CodeFileAnalysis]
    ) -> List[Evidence]:
        """
        Evidence derived from file extensions / detected languages.
        Uses LOC-weighted scoring for better proficiency estimates.
        """
        evidence: List[Evidence] = []

        # First pass: gather LOC per language
        loc_per_lang: Dict[str, int] = {}
        for fa in file_analyses:
            lang = fa.language
            if not lang:
                continue
            loc_per_lang[lang] = loc_per_lang.get(lang, 0) + fa.total_lines

        if not loc_per_lang:
            return evidence

        max_loc = max(loc_per_lang.values()) or 1

        # TAXONOMY might be a dict or a set; handle both cases
        is_tax_dict = isinstance(TAXONOMY, dict)

        for lang, loc in loc_per_lang.items():
            rel_weight = loc / max_loc

            if is_tax_dict:
                entry = TAXONOMY.get(lang) or TAXONOMY.get(lang.lower())
                if isinstance(entry, dict):
                    skill_name = entry.get("canonical_name") or entry.get("name") or lang
                else:
                    skill_name = str(entry) if entry is not None else lang
            else:
                # TAXONOMY is a set or something non-dict; just use the language name
                skill_name = lang

            evidence.append(
                Evidence(
                    skill=skill_name,
                    source="language_usage",
                    raw=skill_name,
                    file_path="*",
                    weight=0.4 + 0.4 * rel_weight,
                )
            )

        return evidence

    
    def _dependency_evidence(self) -> List[Evidence]:
        evidence: List[Evidence] = []

        for path in self._iter_project_files():
            if not path.is_file():
                continue

            if path.name not in DEPENDENCY_FILES:
                continue   # <-- ignore random docs

            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            for pattern, skill in self._iter_pattern_pairs(DEP_TO_SKILL):
                if hasattr(pattern, "search"):
                    match = pattern.search(text)
                else:
                    match = pattern in text
                if match:
                    evidence.append(
                        Evidence(
                            skill=skill,
                            source="dependency",
                            raw=getattr(pattern, "pattern", str(pattern)),
                            file_path=str(path.relative_to(self.root_dir)),
                            weight=0.7,
                        )
                    )

        return evidence

    def _config_evidence(self) -> List[Evidence]:
        """
        Evidence from config-file naming conventions (e.g., next.config.js, Dockerfile).
        """
        evidence: List[Evidence] = []

        for path in self._iter_project_files():
            if not path.is_file():
                continue

            rel_name = path.name

            for checker, skill, source_kind in self._iter_config_hints(KNOWN_CONFIG_HINTS):
                if checker(rel_name):
                    evidence.append(
                        Evidence(
                            skill=skill,
                            source=source_kind,
                            raw=rel_name,
                            file_path=str(path.relative_to(self.root_dir)),
                            weight=0.8,
                        )
                    )

        return evidence

    def _extract_snippet_skills(self, file_analyses: List[CodeFileAnalysis]) -> None:
        """
        For each code file, scan its text once and record which snippet patterns matched.
        This avoids re-reading files in _snippet_evidence and also gates patterns
        by language to keep Analyze Skills fast.

        Uses language gating from LANG_TO_ALLOWED_SNIPPET_SKILLS to avoid running
        JS regexes on Python files, etc.
        """
        for fa in file_analyses:
            full_path = fa.path

            if not isinstance(full_path, Path):
                full_path = Path(full_path)
            try:
                text = full_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            lang = (fa.language or "").lower()
            allowed_skills = LANG_TO_ALLOWED_SNIPPET_SKILLS.get(lang, [])

            if not allowed_skills:
                continue

            for skill in allowed_skills:
            # Count matches per skill
                for pattern, skill in self._iter_pattern_pairs(SNIPPET_PATTERNS):
                    # If we have a whitelist for this language, skip skills that don't apply
                    if allowed_skills is not None and skill not in allowed_skills:
                        continue

                    if hasattr(pattern, "findall"):
                        matches = len(pattern.findall(text))
                    else:
                        matches = text.count(str(pattern))

                    if matches > 0:
                        fa.snippet_matches[skill] = (
                            fa.snippet_matches.get(skill, 0) + matches
                        )

            # Also populate snippet_skills list for backward compatibility
            if fa.snippet_matches:
                fa.snippet_skills.extend(sorted(fa.snippet_matches.keys()))

    def _snippet_evidence(
        self, file_analyses: Iterable[CodeFileAnalysis]
    ) -> List[Evidence]:
        """
        Turn snippet_matches on each file into Evidence entries.
        Weight increases with match count.
        """
        evidence: List[Evidence] = []

        for fa in file_analyses:
            if not fa.snippet_matches:
                continue

            for skill, count in fa.snippet_matches.items():
                weight = min(1.0, 0.3 + 0.1 * count)
                try:
                    file_path = str(fa.path.resolve().relative_to(self.root_dir.resolve()))
                except ValueError:
                    file_path = str(fa.path.resolve())
                evidence.append(
                    Evidence(
                        skill=skill,
                        source="snippet_pattern",
                        raw=f"{skill} x{count}",
                        file_path=file_path,
                        weight=weight,
                    )
                )

        return evidence

    # ------------------------------------------------------------------
    # Building SkillProfileItem objects
    # ------------------------------------------------------------------

    def _build_skill_profiles(
        self, evidence: List[Evidence], stats: Dict[str, Any]
    ) -> List[SkillProfileItem]:
        """
        Aggregate evidence into SkillProfileItem objects with proficiency estimates.
        """
        by_skill: Dict[str, List[Evidence]] = {}
        for e in evidence:
            by_skill.setdefault(e.skill, []).append(e)

        profiles: List[SkillProfileItem] = []
        for skill, ev_list in by_skill.items():
            if not skill:
                continue

            # Estimate proficiency using ProficiencyEstimator
            proficiency = self.prof_estimator.estimate(skill, ev_list, stats)
            confidence = round(min(1.0, 0.3 + 0.1 * len(ev_list) + 0.1 * proficiency), 2)

            profiles.append(
                SkillProfileItem(
                    skill=skill,
                    proficiency=proficiency,
                    confidence=confidence,
                    evidence=ev_list,
                )
            )

        # Sort by proficiency, then confidence
        profiles.sort(
            key=lambda p: (p.proficiency, p.confidence),
            reverse=True,
        )
        return profiles

    # ------------------------------------------------------------------
    # Internal helpers: dimensions
    # ------------------------------------------------------------------

    def _compute_dimensions(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute meta-skill dimensions from project statistics.
        """
        overall = stats.get("overall", {}) or {}
        per_lang = stats.get("per_language", {}) or {}

        # --- Testing discipline ---
        # FIX: Directly use the 'test_file_ratio' from the overall stats, which is pre-calculated.
        test_ratio = overall.get("test_file_ratio", 0.0)
        test_score = min(1.0, test_ratio / 0.4)  # 0.4+ tests/code ~= strong
        testing_level = self._level_from_score(test_score)

        testing_dim = {
            "score": round(test_score, 2),
            "level": testing_level,
            "raw": {
                "test_file_ratio": test_ratio,
                # FIX: Use the correct keys from overall stats
                "num_test_files": overall.get("num_test_files", 0),
                "num_code_files": overall.get("num_code_files", 0),
                "total_files": overall.get("file_count", 0),
            },
        }

        # --- Documentation habits ---
        comment_ratio = overall.get("comment_ratio", 0.0)
        # e.g. 0.05 is minimal, 0.2+ is solid
        doc_score = min(1.0, comment_ratio / 0.2)
        doc_level = self._level_from_score(doc_score)

        doc_dim = {
            "score": round(doc_score, 2),
            "level": doc_level,
            "raw": {
                "comment_ratio": comment_ratio,
            },
        }

        # --- Modularity ---
        avg_funcs = overall.get("avg_functions_per_file", 0.0)
        max_func_len = overall.get("max_function_length", 0)

        # heuristic: more functions and shorter max function is better
        modularity_score = 0.0
        if avg_funcs >= 3:
            modularity_score += 0.5
        if max_func_len > 0 and max_func_len <= 50: # FIX: Added check for > 0
            modularity_score += 0.5
        elif max_func_len > 0 and max_func_len <= 100: # FIX: Added check for > 0
            modularity_score += 0.25

        modularity_score = min(1.0, modularity_score)
        modularity_level = self._level_from_score(modularity_score)

        modularity_dim = {
            "score": round(modularity_score, 2),
            "level": modularity_level,
            "raw": {
                "avg_functions_per_file": avg_funcs,
                "max_function_length": max_func_len,
            },
        }

        # --- Language depth ---
        # FIX: Correctly calculate total_loc and language count
        total_loc = overall.get("total_lines_of_code", 0)
        lang_count = len(per_lang) if isinstance(per_lang, dict) else 0

        # A simple proxy: fraction of languages above a LOC threshold
        depth_languages = {
            lang: data["loc"]
            for lang, data in per_lang.items()
            if isinstance(data, dict) and data.get("loc", 0) >= 500  # arbitrary "non-toy" threshold
        }

        depth_ratio = len(depth_languages) / max(1, lang_count) if lang_count > 0 else 0.0

        lang_depth_score = min(
            1.0, 0.5 + depth_ratio * 0.5
        )  # base 0.5 for having code at all
        lang_depth_level = self._level_from_score(lang_depth_score)

        lang_depth_dim = {
            "score": round(lang_depth_score, 2),
            "level": lang_depth_level,
            "raw": {
                "languages": {
                    lang: {"loc": loc} for lang, loc in depth_languages.items()
                },
                "total_loc": total_loc,
                "language_count": lang_count,
            },
        }

        dimensions = {
            "testing_discipline": testing_dim,
            "documentation_habits": doc_dim,
            "modularity": modularity_dim,
            "language_depth": lang_depth_dim,
        }

        return dimensions

    def _level_from_score(self, score: float) -> str:
        """Convert numeric score to human-readable level."""
        if score >= 0.75:
            return "strong"
        if score >= 0.5:
            return "good"
        if score >= 0.25:
            return "ok"
        return "needs_improvement"
