"""
Proficiency scoring for detected skills.
"""

from __future__ import annotations
from typing import Any, Dict, List

from .skill_models import Evidence


class ProficiencyEstimator:
    """
    Compute a heuristic 0..1 proficiency score per skill (capped by caller).
    """

    def estimate(self, skill: str, evidence: List[Evidence], stats: Dict[str, Any]) -> float:
        """
        Produce a heuristic 0..1 proficiency score per skill.
        Mirrors the original _estimate_proficiency implementation.
        """
        stats = stats or {}

        # ---- Python proficiency ----
        if skill == "Python":
            py = stats.get("python", {})
            files = max(1, int(py.get("files", 0)))
            defs = py.get("defs", 0)
            async_defs = py.get("async_defs", 0)
            classes = py.get("classes", 0)
            with_blocks = py.get("with_blocks", 0)
            doc_quotes = py.get("doc_quotes", 0)
            type_arrows = py.get("type_arrows", 0)
            type_params = py.get("type_params", 0)
            test_files = py.get("test_files", 0)
            lines = max(1, int(py.get("lines", 1)))

            # usage_depth: async + classes + context managers per KLOC
            kloc = lines / 1000.0
            usage_depth = _sigmoid((async_defs + classes + with_blocks) / max(1.0, kloc * 10.0))

            # typing: presence of annotations (very rough)
            typing_ratio = _clip01((type_arrows + type_params) / max(1, defs * 1.5))

            # docs: docstring density (approx: doc quotes / defs)
            doc_ratio = _clip01(doc_quotes / max(1, defs * 1.2))

            # testing: share of test files among python files
            test_ratio = _clip01(test_files / max(1, files))

            proficiency = round((
                0.40 * usage_depth +
                0.25 * typing_ratio +
                0.20 * doc_ratio +
                0.15 * test_ratio
            ),2)
            if any(e.skill == "PyTest" for e in evidence):
                proficiency = min(proficiency + 0.05, 0.98)
            return proficiency

        # ---- Docker proficiency ----
        if skill == "Docker":
            dk = stats.get("docker", {})
            dockerfiles = dk.get("dockerfiles", 0)
            compose = dk.get("compose", 0)
            multistage = dk.get("multistage", 0)
            healthcheck = dk.get("healthcheck", 0)

            if dockerfiles == 0 and compose == 0:
                return 0.0

            base = 0.35 if dockerfiles or compose else 0.0
            advanced = 0.0
            if multistage:
                advanced += 0.25
            if healthcheck:
                advanced += 0.15
            if compose:
                advanced += 0.15

            if any(
                e.source in ("build_tool", "linter_config", "test_framework")
                and e.skill in ("Docker", "CI/CD")
                for e in evidence
            ):
                advanced += 0.05

            return _clip01(base + advanced)

        # ---- Frameworks / libraries (quick baseline) ----
        framework_like = {
            "Django", "Flask", "FastAPI", "React", "Next.js", "Angular", "Vue", "Svelte",
            "Spring", ".NET", "ASP.NET", "Express", "Unity", "Unreal Engine",
        }
        if skill in framework_like:
            hits = 0
            for e in evidence:
                if e.skill == skill and e.source in ("import_statement", "framework_convention", "dependency"):
                    hits += 1
            return [0.0, 0.45, 0.62, 0.75][min(3, hits)]

        # ---- Testing tools (PyTest/JUnit/Jest/etc.) ----
        if skill in {"PyTest", "JUnit", "Jest", "Vitest", "Cypress", "Playwright"}:
            py_tests = stats.get("python", {}).get("test_files", 0)
            if py_tests >= 3:
                return 0.72
            if py_tests >= 1:
                return 0.55
            return 0.4 if any(e.source in ("dependency", "test_framework") for e in evidence) else 0.2

        # ---- Databases / Cloud (presence-driven baseline) ----
        if skill in {"PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "AWS", "GCP", "Azure", "Firebase"}:
            hits = sum(
                1
                for e in evidence
                if e.skill == skill and e.source in ("dependency", "build_tool", "framework_convention")
            )
            return [0.0, 0.35, 0.5, 0.65][min(3, hits)]

        # default: mild baseline proportional to evidence variety
        distinct_sources = len({e.source for e in evidence if e.skill == skill})
        return [0.0, 0.3, 0.45, 0.6][min(3, distinct_sources)]


def _sigmoid(x: float) -> float:
    import math
    return 1.0 / (1.0 + math.exp(-3.0 * (x - 0.5)))  # centered ~0.5


def _clip01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)
