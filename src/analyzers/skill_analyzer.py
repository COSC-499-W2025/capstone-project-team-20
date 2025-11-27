from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from .code_metrics_analyzer import CodeMetricsAnalyzer, CodeFileAnalysis
from .skill_models import Evidence, SkillProfileItem, TAXONOMY
from .skill_patterns import DEP_TO_SKILL, SNIPPET_PATTERNS, KNOWN_CONFIG_HINTS

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
        """
        evidence: List[Evidence] = []

        for fa in file_analyses:
            if not fa.language:
                continue

            skill_name = fa.language
            if skill_name not in TAXONOMY:
                # Still allow unknown languages, but we treat them as low-priority
                pass

            evidence.append(
                Evidence(
                    skill=skill_name,
                    source="language_usage",
                    raw=skill_name,
                    file_path=str(fa.path.relative_to(self.root_dir)),
                    weight=0.5,
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

        for path in self.root_dir.rglob("*"):
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

        for path in self.root_dir.rglob("*"):
            if not path.is_file():
                continue

            rel_name = path.name

            for pattern, skill, source_kind in KNOWN_CONFIG_HINTS:
                if pattern.match(rel_name):
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
        """
        for fa in file_analyses:
            full_path = fa.path
            try:
                text = full_path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue

            lang = (fa.language or "").lower()
            allowed_skills = LANG_TO_ALLOWED_SNIPPET_SKILLS.get(lang)

            matched_skills: Set[str] = set()
            for pattern, skill, source_kind in SNIPPET_PATTERNS:
                # If we have a whitelist for this language, skip skills that don't apply
                if allowed_skills is not None and skill not in allowed_skills:
                    continue
                if pattern.search(text):
                    matched_skills.add(skill)

            if matched_skills:
                fa.snippet_skills.extend(sorted(matched_skills))


    def _snippet_evidence(
        self, file_analyses: Iterable[CodeFileAnalysis]
    ) -> List[Evidence]:
        """
        Turn snippet_skills on each file into Evidence entries.
        """
        evidence: List[Evidence] = []
        for fa in file_analyses:
            if not fa.snippet_skills:
                continue

            rel_path = str(fa.path.relative_to(self.root_dir))
            for skill in fa.snippet_skills:
                evidence.append(
                    Evidence(
                        skill=skill,
                        source="snippet_pattern",
                        raw=f"snippet in {rel_path}",
                        file_path=rel_path,
                        weight=0.6,
                    )
                )

        return evidence

    # ------------------------------------------------------------------
    # Building SkillProfileItem objects
    # ------------------------------------------------------------------

    def _build_skill_profiles(
        self, evidence: List[Evidence], stats: Dict[str, Any]
    ) -> List[SkillProfileItem]:
        by_skill: Dict[str, List[Evidence]] = {}
        for e in evidence:
            by_skill.setdefault(e.skill, []).append(e)

        profiles: List[SkillProfileItem] = []
        for skill, ev_list in by_skill.items():
            if not skill:
                continue
            profiles.append(
                SkillProfileItem(
                    skill=skill,
                    evidence=ev_list,
                )
            )

        # Sort by “importance” = evidence count
        profiles.sort(
            key=lambda p: len(p.evidence),
            reverse=True,
        )
        return profiles

    # ------------------------------------------------------------------
    # Internal helpers: dimensions
    # ------------------------------------------------------------------

    def _compute_dimensions(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        overall = stats.get("overall", {})
        per_lang = stats.get("per_language", {})

        # --- Testing discipline ---
        test_ratio = overall.get("test_file_ratio", 0.0)
        test_score = min(1.0, test_ratio / 0.4)  # 0.4+ tests/code ~= strong
        testing_level = self._level_from_score(test_score)

        testing_dim = {
            "score": round(test_score, 2),
            "level": testing_level,
            "raw": {
                "test_file_ratio": test_ratio,
                "num_test_files": overall.get("num_test_files", 0),
                "num_code_files": overall.get("num_code_files", 0),
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
        if max_func_len <= 50:
            modularity_score += 0.5
        elif max_func_len <= 100:
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
        total_loc = sum(lang_stats.get("loc", 0) for lang_stats in per_lang.values())
        # A simple proxy: fraction of languages above a LOC threshold
        depth_languages = {
            lang: data["loc"]
            for lang, data in per_lang.items()
            if data.get("loc", 0) >= 500  # arbitrary "non-toy" threshold
        }
        depth_ratio = len(depth_languages) / max(1, len(per_lang))
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
            },
        }

        return {
            "testing_discipline": testing_dim,
            "documentation_habits": doc_dim,
            "modularity": modularity_dim,
            "language_depth": lang_depth_dim,
        }

    def _level_from_score(self, score: float) -> str:
        if score >= 0.75:
            return "strong"
        if score >= 0.5:
            return "good"
        if score >= 0.25:
            return "ok"
        return "needs_improvement"
