"""
Regex patterns and config-names for skill extraction.
"""

import re
from typing import List, Tuple


DEP_TO_SKILL: List[Tuple[re.Pattern, str]] = [
    # JS/TS
    (re.compile(r"react(-dom)?", re.I), "React"),
    (re.compile(r"\bnext\b", re.I), "Next.js"),
    (re.compile(r"angular", re.I), "Angular"),
    (re.compile(r"vue", re.I), "Vue"),
    (re.compile(r"svelte", re.I), "Svelte"),
    (re.compile(r"(node|express)\b", re.I), "Node.js"),
    (re.compile(r"typescript", re.I), "TypeScript"),
    (re.compile(r"webpack", re.I), "Webpack"),
    (re.compile(r"vite", re.I), "Vite"),
    (re.compile(r"babel", re.I), "Babel"),
    (re.compile(r"eslint", re.I), "ESLint"),
    (re.compile(r"prettier", re.I), "Prettier"),
    (re.compile(r"jest", re.I), "Jest"),
    (re.compile(r"vitest", re.I), "Vitest"),
    (re.compile(r"cypress", re.I), "Cypress"),
    (re.compile(r"playwright", re.I), "Playwright"),
    # Python
    (re.compile(r"django", re.I), "Django"),
    (re.compile(r"flask", re.I), "Flask"),
    (re.compile(r"fastapi", re.I), "FastAPI"),
    (re.compile(r"pandas", re.I), "Pandas"),
    (re.compile(r"numpy", re.I), "NumPy"),
    (re.compile(r"(scikit-learn|sklearn)", re.I), "scikit-learn"),
    (re.compile(r"matplotlib", re.I), "Matplotlib"),
    (re.compile(r"(pytest|py\.test)", re.I), "PyTest"),
    (re.compile(r"(pipenv|poetry)", re.I), "Poetry"),
    # Java
    (re.compile(r"(spring|spring-boot)", re.I), "Spring"),
    (re.compile(r"junit", re.I), "JUnit"),
    (re.compile(r"maven", re.I), "Maven"),
    (re.compile(r"gradle", re.I), "Gradle"),
    # C++ / Tooling
    (re.compile(r"cmake", re.I), "CMake"),
    (re.compile(r"conan", re.I), "Conan"),
    # .NET
    (re.compile(r"(asp\.?net|entityframework|efcore)", re.I), "ASP.NET"),
    (re.compile(r"(microsoft\.net|dotnet)", re.I), ".NET"),
    # Game
    (re.compile(r"unity", re.I), "Unity"),
    (re.compile(r"(unreal|ue[45]?)", re.I), "Unreal Engine"),
    # DB / Cloud
    (re.compile(r"postgres", re.I), "PostgreSQL"),
    (re.compile(r"mysql", re.I), "MySQL"),
    (re.compile(r"sqlite", re.I), "SQLite"),
    (re.compile(r"mongodb", re.I), "MongoDB"),
    (re.compile(r"redis", re.I), "Redis"),
    (re.compile(r"aws", re.I), "AWS"),
    (re.compile(r"(gcp|google-?cloud)", re.I), "GCP"),
    (re.compile(r"azure", re.I), "Azure"),
    (re.compile(r"firebase", re.I), "Firebase"),
    # Other
    (re.compile(r"graphql", re.I), "GraphQL"),
    (re.compile(r"grpc", re.I), "gRPC"),
]


SNIPPET_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    # imports / includes
    (re.compile(r"^\s*import\s+.*\s+from\s+['\"]react['\"]", re.M), "React", "import_statement"),
    (re.compile(r"^\s*import\s+.*\s+from\s+['\"]next['\"]", re.M), "Next.js", "import_statement"),
    (re.compile(r"^\s*from\s+django\s+import\s+", re.M), "Django", "import_statement"),
    (re.compile(r"^\s*import\s+flask", re.M), "Flask", "import_statement"),
    (re.compile(r"^\s*from\s+fastapi\s+import\s+", re.M), "FastAPI", "import_statement"),
    (re.compile(r"#include\s*<gtest/gtest\.h>"), "C++", "import_statement"),
    # language idioms
    (re.compile(r"\busing\s+namespace\s+std\b"), "C++", "snippet_pattern"),
    (re.compile(r"\bstd::vector<\w+>"), "C++", "snippet_pattern"),
    (re.compile(r"\bConsole\.WriteLine\("), "C#", "snippet_pattern"),
    (re.compile(r"\bSystem\.Collections\b"), "C#", "snippet_pattern"),
    (re.compile(r"\bdef\s+\w+\(.*\):"), "Python", "snippet_pattern"),
    (re.compile(r"\bpublic\s+class\s+\w+"), "Java", "snippet_pattern"),
    (re.compile(r"\bfn\s+\w+\s*\("), "Rust", "snippet_pattern"),
    # tools
    (re.compile(r"\bcmake_minimum_required\b", re.I), "CMake", "build_tool"),
    (re.compile(r"\badd_executable\s*\(", re.I), "CMake", "build_tool"),
]


KNOWN_CONFIG_HINTS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(r"^next\.config\.(js|ts)$"), "Next.js", "framework_convention"),
    (re.compile(r"^angular\.json$"), "Angular", "framework_convention"),
    (re.compile(r"^vite\.config\.(js|ts)$"), "Vite", "build_tool"),
    (re.compile(r"^webpack\.config\.(js|cjs|mjs|ts)$"), "Webpack", "build_tool"),
    (re.compile(r"^CMakeLists\.txt$"), "CMake", "build_tool"),
    (re.compile(r"^Dockerfile$"), "Docker", "build_tool"),
    (re.compile(r"^docker-compose\..*"), "Docker", "build_tool"),
]
