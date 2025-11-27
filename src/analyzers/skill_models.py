"""
Shared data models and taxonomy for skill extraction.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Set

from .language_detector import LANGUAGE_MAP  # maps ext (no dot) -> language


@dataclass
class Evidence:
    skill: str
    source: str         # "language_usage" | "dependency" | "snippet_pattern" | "build_tool" | ...
    raw: str            # matched token (dep name, line, filename)
    file_path: Optional[str] = None
    weight: float = 0.5


@dataclass
class SkillProfileItem:
    skill: str
    evidence: List[Evidence]

    # Extra resume-friendly fields
    primary_language: Optional[str] = None
    total_loc: int = 0
    project_count: int = 1   # later used when aggregating across projects
    tags: Set[str] = field(default_factory=set)


# Skills that are not pure languages (frameworks, tools, etc.)
NON_LANGUAGE_TAXONOMY: Set[str] = {
    # Frameworks / runtimes
    "Node.js", "React", "Next.js", "Angular", "Vue", "Svelte",
    ".NET", "ASP.NET", "Spring", "Django", "Flask", "FastAPI", "Express",
    "Unity", "Unreal Engine", "Qt", "Electron",

    # Data & ML
    "NumPy", "Pandas", "scikit-learn", "PyTorch", "TensorFlow", "Matplotlib",

    # Tooling
    "Docker", "Kubernetes", "Git", "Maven", "Gradle", "NPM", "Yarn", "PNPM", "Vite",
    "Webpack", "Babel", "ESLint", "Prettier", "Jest", "Mocha", "PyTest", "JUnit",
    "CMake", "Make", "Conan", "Poetry", "Pip", "Pipenv",

    # Cloud/DB
    "AWS", "GCP", "Azure", "Firebase",
    "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis",

    # Testing/Other
    "Playwright", "Cypress", "Selenium", "Vitest",
    "REST", "GraphQL", "gRPC", "CI/CD",
}

# Subset of NON_LANGUAGE_TAXONOMY that we treat as “frameworks”
KNOWN_FRAMEWORKS: Set[str] = {
    "React", "Next.js", "Angular", "Vue", "Svelte",
    "Django", "Flask", "FastAPI", "Spring", "ASP.NET",
    "Node.js", "Express",
    "Unity", "Unreal Engine",
}


def _taxonomy_with_languages() -> Set[str]:
    langs = {v for v in LANGUAGE_MAP.values()}
    return set(langs) | NON_LANGUAGE_TAXONOMY


TAXONOMY: Set[str] = _taxonomy_with_languages()
