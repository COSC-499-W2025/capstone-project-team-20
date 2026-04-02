"""
Regex patterns and config-names for skill extraction.
"""

import re
from typing import List, Optional, Set, Tuple

# Dependency file groups — patterns are only matched against their relevant files
JS_DEP_FILES: Set[str] = {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}
PYTHON_DEP_FILES: Set[str] = {"requirements.txt", "pyproject.toml", "Pipfile", "Pipfile.lock", "environment.yml", "poetry.lock"}
JAVA_DEP_FILES: Set[str] = {"pom.xml", "build.gradle", "build.gradle.kts"}
DOTNET_DEP_FILES: Set[str] = {"*.csproj", "packages.config", "nuget.config"}
GO_DEP_FILES: Set[str] = {"go.mod"}
CPP_DEP_FILES: Set[str] = {"CMakeLists.txt", "conanfile.txt", "conanfile.py"}
ALL_DEP_FILES: Optional[Set[str]] = None  # None = match any dependency file

# Each entry: (pattern, skill, allowed_dep_files)
# allowed_dep_files=None means the pattern runs against all dependency files.
DEP_TO_SKILL: List[Tuple[re.Pattern, str, Optional[Set[str]]]] = [
    # JS/TS — only look in JS package files
    (re.compile(r"\"react(-dom)?\"", re.I), "React", JS_DEP_FILES),
    (re.compile(r"\"next\"", re.I), "Next.js", JS_DEP_FILES),
    (re.compile(r"\"@angular/core\"", re.I), "Angular", JS_DEP_FILES),
    (re.compile(r"\"vue\"", re.I), "Vue", JS_DEP_FILES),
    (re.compile(r"\"svelte\"", re.I), "Svelte", JS_DEP_FILES),
    (re.compile(r"\"express\"", re.I), "Node.js", JS_DEP_FILES),
    (re.compile(r"\"typescript\"", re.I), "TypeScript", JS_DEP_FILES),
    (re.compile(r"\"webpack\"", re.I), "Webpack", JS_DEP_FILES),
    (re.compile(r"\"vite\"", re.I), "Vite", JS_DEP_FILES),
    (re.compile(r"\"jest\"", re.I), "Jest", JS_DEP_FILES),
    (re.compile(r"\"vitest\"", re.I), "Vitest", JS_DEP_FILES),
    (re.compile(r"\"cypress\"", re.I), "Cypress", JS_DEP_FILES),
    (re.compile(r"\"@playwright/", re.I), "Playwright", JS_DEP_FILES),
    (re.compile(r"\"tailwindcss\"", re.I), "Tailwind", JS_DEP_FILES),
    (re.compile(r"\"bootstrap\"", re.I), "Bootstrap", JS_DEP_FILES),
    (re.compile(r"\"(@reduxjs/toolkit|redux)\"", re.I), "Redux", JS_DEP_FILES),
    # Python — only look in Python dep files
    (re.compile(r"\bdjango\b", re.I), "Django", PYTHON_DEP_FILES),
    (re.compile(r"\bflask\b", re.I), "Flask", PYTHON_DEP_FILES),
    (re.compile(r"\bfastapi\b", re.I), "FastAPI", PYTHON_DEP_FILES),
    (re.compile(r"\bpandas\b", re.I), "Pandas", PYTHON_DEP_FILES),
    (re.compile(r"\bnumpy\b", re.I), "NumPy", PYTHON_DEP_FILES),
    (re.compile(r"(scikit-learn|sklearn)", re.I), "scikit-learn", PYTHON_DEP_FILES),
    (re.compile(r"\bmatplotlib\b", re.I), "Matplotlib", PYTHON_DEP_FILES),
    (re.compile(r"(pytest|py\.test)", re.I), "PyTest", PYTHON_DEP_FILES),
    (re.compile(r"\bpoetry\b", re.I), "Poetry", PYTHON_DEP_FILES),
    (re.compile(r"\bplaywright\b", re.I), "Playwright", PYTHON_DEP_FILES),
    # Java — only look in Java build files
    (re.compile(r"spring(-boot)?", re.I), "Spring", JAVA_DEP_FILES),
    (re.compile(r"\bjunit\b", re.I), "JUnit", JAVA_DEP_FILES),
    (re.compile(r"\bhibernate\b", re.I), "Hibernate", JAVA_DEP_FILES),
    # C++ / Tooling
    (re.compile(r"\bcmake\b", re.I), "CMake", CPP_DEP_FILES),
    (re.compile(r"\bconan\b", re.I), "Conan", CPP_DEP_FILES),
    # .NET
    (re.compile(r"(asp\.?net|entityframework|efcore)", re.I), "ASP.NET", DOTNET_DEP_FILES),
    (re.compile(r"(microsoft\.net|dotnet)", re.I), ".NET", DOTNET_DEP_FILES),
    # Game — Unity/Unreal are never listed in standard dep files; detected via config/snippet only
    # DB / Cloud — these are safe to match broadly since names are distinctive
    (re.compile(r"\bpostgres(ql)?\b", re.I), "PostgreSQL", ALL_DEP_FILES),
    (re.compile(r"\bmysql\b", re.I), "MySQL", ALL_DEP_FILES),
    (re.compile(r"\bsqlite\b", re.I), "SQLite", ALL_DEP_FILES),
    (re.compile(r"\bmongodb\b", re.I), "MongoDB", ALL_DEP_FILES),
    (re.compile(r"\bredis\b", re.I), "Redis", ALL_DEP_FILES),
    (re.compile(r"\baws\b", re.I), "AWS", ALL_DEP_FILES),
    (re.compile(r"google-cloud-", re.I), "GCP", ALL_DEP_FILES),
    (re.compile(r"\bazure\b", re.I), "Azure", ALL_DEP_FILES),
    (re.compile(r"\bfirebase\b", re.I), "Firebase", ALL_DEP_FILES),
    # Other
    (re.compile(r"\bgraphql\b", re.I), "GraphQL", ALL_DEP_FILES),
    (re.compile(r"\bgrpc\b", re.I), "gRPC", ALL_DEP_FILES),
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
    # Unity: ProjectSettings folder or .unity scene files are definitive signals
    (re.compile(r"^ProjectSettings$", re.I), "Unity", "framework_convention"),
    (re.compile(r"\.unity$", re.I), "Unity", "framework_convention"),
    # Unreal: .uproject file is the canonical signal
    (re.compile(r"\.uproject$", re.I), "Unreal Engine", "framework_convention"),
]
