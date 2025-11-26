from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

import os

from src.ZipParser import IGNORED_DIRS, IGNORED_EXTS, IGNORED_FILES

from .skill_models import Evidence, SkillProfileItem, TAXONOMY
from .skill_patterns import DEP_TO_SKILL, SNIPPET_PATTERNS, KNOWN_CONFIG_HINTS
from .skill_proficiency import ProficiencyEstimator
from .code_metrics_analyzer import CodeMetricsAnalyzer, CodeFileAnalysis


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

    # ------------------------------------------------------------------
    # Internal helpers for walking the project tree with ignores
    # ------------------------------------------------------------------

    def _iter_project_files(self) -> Iterable[Path]:
        """
        Iterate over regular files under root_dir while respecting
        ignored_directories.yml via the shared IGNORED_* sets loaded in ZipParser.
        This is used for dependency and config evidence so we don't accidentally
        scan things like node_modules, .venv, build artefacts, etc.
        """
        root_str = str(self.root_dir)

        for root, dirs, files in os.walk(root_str):
            root_path = Path(root)

            # 1) Prune directories using IGNORED_DIRS
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

            # 2) Yield files that are not filtered by extension/filename
            for fname in files:
                file_path = root_path / fname
                rel = file_path.relative_to(self.root_dir)
                ext = rel.suffix.lstrip(".").lower()
                filename = rel.name.lower()

                if ext in IGNORED_EXTS:
                    continue
                if filename in IGNORED_FILES:
                    continue

                yield file_path

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
    # Stats used by ProficiencyEstimator
    # ------------------------------------------------------------------

    def _build_stats(self, file_analyses: List[CodeFileAnalysis]) -> Dict[str, Any]:
        """
        Produce a stats dict for ProficiencyEstimator from code metrics.
        """
        summary = self.metrics_analyzer.summarize(file_analyses)
        overall = summary.get("overall", {})
        per_lang = summary.get("per_language", {})

        stats: Dict[str, Any] = {
            "overall": overall,
            "per_language": per_lang,
        }

        return stats

    # ------------------------------------------------------------------
    # Evidence extractors
    # ------------------------------------------------------------------

    def _language_evidence(
        self, file_analyses: List[CodeFileAnalysis]
    ) -> List[Evidence]:
        """
        Produce Evidence from detected languages (per CodeMetricsAnalyzer).
        """
        evidence: List[Evidence] = []

        # Count LOC per language for rough weighting
        loc_per_lang: Dict[str, int] = {}
        for fa in file_analyses:
            lang = fa.language
            if not lang:
                continue
            loc_per_lang[lang] = loc_per_lang.get(lang, 0) + fa.total_lines

        if not loc_per_lang:
            return evidence

        max_loc = max(loc_per_lang.values()) or 1

        for lang, loc in loc_per_lang.items():
            rel_weight = loc / max_loc
            # Map language to taxonomy skill name if defined
            skill_name = TAXONOMY.get(lang, {}).get("canonical_name", lang)

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
        """
        Walks text-like dependency/config files and applies DEP_TO_SKILL patterns.
        """
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

            for pattern, skill in DEP_TO_SKILL:
                if pattern.search(text):
                    evidence.append(
                        Evidence(
                            skill=skill,
                            source="dependency",
                            raw=pattern.pattern,
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

            for hint in KNOWN_CONFIG_HINTS:
                if hint.matches(rel_name):
                    skill = hint.skill
                    source_kind = hint.source_kind

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
        This avoids re-reading files in _snippet_evidence.
        """
        for fa in file_analyses:
            try:
                text = fa.path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            for pattern, skill in SNIPPET_PATTERNS:
                matches = len(pattern.findall(text))
                if matches > 0:
                    fa.snippet_matches[skill] = (
                        fa.snippet_matches.get(skill, 0) + matches
                    )

    def _snippet_evidence(self, file_analyses: List[CodeFileAnalysis]) -> List[Evidence]:
        """
        Turn snippet pattern matches into Evidence objects.
        """
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
        # Group evidence by skill
        by_skill: Dict[str, List[Evidence]] = {}
        for ev in evidence_list:
            by_skill.setdefault(ev.skill, []).append(ev)

        profiles: List[SkillProfileItem] = []

        for skill, evs in by_skill.items():
            proficiency = self.prof_estimator.estimate(skill, evs, stats)
            confidence = min(
                1.0, 0.3 + 0.1 * len(evs) + 0.1 * proficiency  # simple heuristic
            )

            profiles.append(
                SkillProfileItem(
                    skill=skill,
                    proficiency=proficiency,
                    confidence=confidence,
                    evidence=evs,
                )
            )

        # Sort more relevant skills first
        profiles.sort(key=lambda s: (s.proficiency, s.confidence), reverse=True)
        return profiles

    # ------------------------------------------------------------------
    # Dimensions (meta-skills)
    # ------------------------------------------------------------------

    def _compute_dimensions(self, stats: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Computes coarse-grained dimensions (testing discipline, documentation habits,
        modularity, language depth) from stats.
        """
        overall = stats.get("overall", {})
        per_lang = stats.get("per_language", {})

        # Testing discipline: ratio of test files to total files
        total_files = overall.get("file_count", 0) or 1
        total_test_files = sum(
            lang_stats.get("test_file_count", 0) for lang_stats in per_lang.values()
        )
        testing_score = total_test_files / total_files

        # Documentation habits: placeholder for now (could use comment density)
        doc_score = 0.5

        # Modularity: inverse of max function length, clamped
        max_func = overall.get("max_function_length", 0)
        modularity_score = 1.0 / (1.0 + max_func / 50.0) if max_func else 0.5

        # Language depth: number of languages with significant LOC
        lang_depth_score = min(1.0, len(per_lang) / 4.0)

        return {
            "testing_discipline": {
                "score": testing_score,
                "level": self._level_from_score(testing_score),
            },
            "documentation_habits": {
                "score": doc_score,
                "level": self._level_from_score(doc_score),
            },
            "modularity": {
                "score": modularity_score,
                "level": self._level_from_score(modularity_score),
            },
            "language_depth": {
                "score": lang_depth_score,
                "level": self._level_from_score(lang_depth_score),
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
