from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Callable, Tuple

import os

from src.FileCategorizer import FileCategorizer

from .skill_models import Evidence, SkillProfileItem, TAXONOMY
from .skill_patterns import DEP_TO_SKILL, SNIPPET_PATTERNS, KNOWN_CONFIG_HINTS
from .skill_proficiency import ProficiencyEstimator
from .code_metrics_analyzer import CodeMetricsAnalyzer, CodeFileAnalysis


class SkillAnalyzer:
    """
    High-level skill analysis for a single extracted project directory.
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

        # Placeholder for future resume/portfolio bullets built directly here
        resume_suggestions: List[Dict[str, Any]] = []

        return {
            "skills": skills,
            "stats": stats,
            "dimensions": dimensions,
            "resume_suggestions": resume_suggestions,
        }

    # ------------------------------------------------------------------
    # Stats used by ProficiencyEstimator
    # ------------------------------------------------------------------

    def _build_stats(self, file_analyses: List[CodeFileAnalysis]) -> Dict[str, Any]:
        summary = self.metrics_analyzer.summarize(file_analyses)
        overall = summary.get("overall", {})
        per_lang = summary.get("per_language", {})

        return {
            "overall": overall,
            "per_language": per_lang,
        }

    # ------------------------------------------------------------------
    # Evidence extractors
    # ------------------------------------------------------------------

    def _language_evidence(
        self, file_analyses: List[CodeFileAnalysis]
    ) -> List[Evidence]:
        evidence: List[Evidence] = []

        loc_per_lang: Dict[str, int] = {}
        for fa in file_analyses:
            lang = fa.language
            if not lang:
                continue
            loc_per_lang[lang] = loc_per_lang.get(lang, 0) + fa.total_lines

        if not loc_per_lang:
            return evidence

        max_loc = max(loc_per_lang.values()) or 1

        # TAXONOMY might be a dict or a set; tests clearly have it as a set.
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
        text_like_exts = {
            ".txt",
            ".toml",
            ".json",
            ".yaml",
            ".yml",
            ".lock",
            ".ini",
            ".cfg",
            ".xml",
        }

        for path in self._iter_project_files():
            if not path.is_file():
                continue

            if path.suffix.lower() not in text_like_exts:
                continue

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
        for fa in file_analyses:
            try:
                text = fa.path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            for pattern, skill in self._iter_pattern_pairs(SNIPPET_PATTERNS):
                if hasattr(pattern, "findall"):
                    matches = len(pattern.findall(text))
                else:
                    matches = text.count(str(pattern))
                if matches > 0:
                    fa.snippet_matches[skill] = (
                        fa.snippet_matches.get(skill, 0) + matches
                    )

    def _snippet_evidence(self, file_analyses: List[CodeFileAnalysis]) -> List[Evidence]:
        evidence: List[Evidence] = []

        for fa in file_analyses:
            for skill, count in fa.snippet_matches.items():
                weight = min(1.0, 0.3 + 0.1 * count)
                evidence.append(
                    Evidence(
                        skill=skill,
                        source="snippet_pattern",
                        raw=f"{skill} x{count}",
                        file_path=str(fa.path.relative_to(self.root_dir)),
                        weight=weight,
                    )
                )

        return evidence

    # ------------------------------------------------------------------
    # Aggregation into SkillProfileItems
    # ------------------------------------------------------------------

    def _build_skill_profiles(
        self, evidence_list: List[Evidence], stats: Dict[str, Any]
    ) -> List[SkillProfileItem]:
        by_skill: Dict[str, List[Evidence]] = {}
        for ev in evidence_list:
            by_skill.setdefault(ev.skill, []).append(ev)

        profiles: List[SkillProfileItem] = []

        for skill, evs in by_skill.items():
            proficiency = self.prof_estimator.estimate(skill, evs, stats)
            confidence = round(min(1.0, 0.3 + 0.1 * len(evs) + 0.1 * proficiency), 2)

            profiles.append(
                SkillProfileItem(
                    skill=skill,
                    proficiency=proficiency,
                    confidence=confidence,
                    evidence=evs,
                )
            )

        profiles.sort(key=lambda s: (s.proficiency, s.confidence), reverse=True)
        return profiles

    # ------------------------------------------------------------------
    # Dimensions (meta-skills)
    # ------------------------------------------------------------------

    def _compute_dimensions(self, stats: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        overall = stats.get("overall", {}) or {}
        per_lang = stats.get("per_language", {}) or {}

        # Testing discipline: ratio of test files to total files
        total_files = overall.get("total_files", overall.get("file_count", 0)) or 1

        total_test_files = 0
        if isinstance(per_lang, dict):
            for lang_stats in per_lang.values():
                if isinstance(lang_stats, dict):
                    total_test_files += int(lang_stats.get("test_file_count", 0))

        testing_score = total_test_files / total_files

        # Documentation habits: use comment_ratio from overall if available
        doc_score = float(overall.get("comment_ratio", 0.5))

        # Modularity: inverse of max function length, clamped
        max_func = overall.get("max_function_length", 0)
        modularity_score = 1.0 / (1.0 + max_func / 50.0) if max_func else 0.5

        # Language depth: number of languages with significant LOC
        lang_count = len(per_lang) if isinstance(per_lang, dict) else 0
        lang_depth_score = min(1.0, lang_count / 4.0)

        return {
            "testing_discipline": {
                "score": testing_score,
                "level": self._level_from_score(testing_score),
                "raw": {
                    "total_files": total_files,
                    "total_test_files": total_test_files,
                },
            },
            "documentation_habits": {
                "score": doc_score,
                "level": self._level_from_score(doc_score),
                "raw": {},
            },
            "modularity": {
                "score": modularity_score,
                "level": self._level_from_score(modularity_score),
                "raw": {"max_function_length": max_func},
            },
            "language_depth": {
                "score": lang_depth_score,
                "level": self._level_from_score(lang_depth_score),
                "raw": {"language_count": lang_count},
            },
        }

    def _level_from_score(self, score: float) -> str:
        if score >= 0.75:
            return "strong"
        if score >= 0.5:
            return "good"
        if score >= 0.25:
            return "ok"
        return "needs_improvement"
