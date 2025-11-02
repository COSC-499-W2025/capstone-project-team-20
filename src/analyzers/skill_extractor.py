# -*- coding: utf-8 -*-
"""
skill_extractor.py

SkillExtractor builds a ranked skill profile for a project directory or an
in-memory ProjectFolder tree.

What it detects
- Languages (via `LANGUAGE_MAP` file extensions + snippet patterns).
- Frameworks & tools (package manifests, config filenames, imports, snippets).
- Databases / cloud services (presence in deps/configs).
- Testing stacks (e.g., PyTest, JUnit, Jest).

Outputs
- List[SkillProfileItem] sorted by `confidence` (desc):
  - `skill`: name (e.g., "Python", "React", "Docker")
  - `confidence`: 0..1 presence likelihood (evidence-driven, capped at 0.98)
  - `proficiency`: 0..1 heuristic usage depth (capped at 0.98)
  - `evidence`: minimal audit trail (file path / token / source)

Entry points
- Filesystem mode:    `extract_from_path(root_path: Path) -> List[SkillProfileItem]`
- ProjectFolder mode: `extract_from_project_folder(root, get_path, get_bytes) -> List[...]`

Workflow overview:
1) Gather candidate files (rglob or ProjectFolder traversal).
2) Collect light code stats for proficiency (currently deeper for Python & Docker).
3) Build evidence from:
   - File extensions → languages, known config filenames.
   - package.json / requirements*.txt / pyproject.toml / pom.xml / gradle / csproj / etc.
   - Snippet patterns (imports / idioms / build tool markers).
4) Merge & score:
   - Combine evidence per skill with diminishing returns.
   - Apply small “pair” bonuses for common stacks (e.g., Python+Django).
   - Compute heuristic `proficiency` per skill using `code_stats` and evidence variety.
5) Return a ranked list for display or downstream aggregation.

Notes / assumptions:
- No external tools are invoked; regex-level scanning only.
- UTF-8 decoding with "ignore" to be robust on mixed encodings.
- Add specialized proficiency heuristics per framework as needed (extensible).
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Iterable, Tuple, Callable, Any

from .language_detector import LANGUAGE_MAP  # maps ext (no dot) -> language


# ---------- Data models ----------

@dataclass
class Evidence:
    skill: str
    source: str         # "file_extension" | "dependency" | "import_statement" | "build_tool" | ...
    raw: str            # matched token (dep name, line, filename)
    file_path: Optional[str] = None
    weight: float = 0.5

@dataclass
class SkillProfileItem:
    skill: str
    confidence: float
    evidence: List[Evidence] = field(default_factory=list)
    # NEW: heuristic proficiency (0..0.98)
    proficiency: float = 0.0


# ---------- Taxonomy (languages from LANGUAGE_MAP + non-language skills) ----------

NON_LANGUAGE_TAXONOMY = {
    # Frameworks / runtimes
    "Node.js","React","Next.js","Angular","Vue","Svelte",
    ".NET","ASP.NET","Spring","Django","Flask","FastAPI","Express",
    "Unity","Unreal Engine","Qt","Electron",

    # Data & ML
    "NumPy","Pandas","scikit-learn","PyTorch","TensorFlow","Matplotlib",

    # Tooling
    "Docker","Kubernetes","Git","Maven","Gradle","NPM","Yarn","PNPM","Vite",
    "Webpack","Babel","ESLint","Prettier","Jest","Mocha","PyTest","JUnit",
    "CMake","Make","Conan","Poetry","Pip","Pipenv",

    # Cloud/DB
    "AWS","GCP","Azure","Firebase",
    "PostgreSQL","MySQL","SQLite","MongoDB","Redis",

    # Testing/Other
    "Playwright","Cypress","Selenium","Vitest",
    "REST","GraphQL","gRPC","CI/CD",
}

def _taxonomy_with_languages() -> set:
    langs = {v for v in LANGUAGE_MAP.values()}
    return set(langs) | NON_LANGUAGE_TAXONOMY

TAXONOMY = _taxonomy_with_languages()


# ---------- Patterns ----------

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

# Known config filenames → hint
KNOWN_CONFIG_HINTS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(r"^next\.config\.(js|ts)$"), "Next.js", "framework_convention"),
    (re.compile(r"^angular\.json$"), "Angular", "framework_convention"),
    (re.compile(r"^vite\.config\.(js|ts)$"), "Vite", "build_tool"),
    (re.compile(r"^webpack\.config\.(js|cjs|mjs|ts)$"), "Webpack", "build_tool"),
    (re.compile(r"^CMakeLists\.txt$"), "CMake", "build_tool"),
    (re.compile(r"^Dockerfile$"), "Docker", "build_tool"),
    (re.compile(r"^docker-compose\..*"), "Docker", "build_tool"),
]


# ---------- SkillExtractor ----------

class SkillExtractor:
    def __init__(self, read_limit_bytes: int = 4096):
        self.read_limit = read_limit_bytes

    # Mode A: analyze a normal filesystem directory (repo or plain folder)
    def extract_from_path(self, root_path: Path) -> List[SkillProfileItem]:
        files = [p for p in root_path.rglob("*") if p.is_file()]
        # Also collect lightweight code stats for proficiency
        code_stats = self._collect_code_stats_fs(files, self._default_fs_reader)
        return self._extract(files, file_reader=self._default_fs_reader, code_stats=code_stats)

    # Mode B: analyze your in-memory ProjectFolder tree
    def extract_from_project_folder(
        self,
        root_folder: Any,
        get_path: Callable[[Any], str],
        get_bytes: Callable[[Any, int], bytes],
    ) -> List[SkillProfileItem]:
        project_files: List[Any] = []
        stack = [root_folder]
        while stack:
            cur = stack.pop()
            for f in getattr(cur, "children", []) or []:
                project_files.append(f)
            for sub in getattr(cur, "subdir", []) or []:
                stack.append(sub)

        wrapped = []
        for f in project_files:
            p = get_path(f)
            wrapped.append((_PseudoPath(p), f))  # (pseudo path for ext/name), original obj

        code_stats = self._collect_code_stats_pf(wrapped, get_bytes)
        return self._extract_projectfiles(
            wrapped,
            get_bytes=get_bytes,
            code_stats=code_stats,
        )

    # ---------- core pipeline (shared) ----------

    def _extract(
        self,
        fs_files: List[Path],
        file_reader: Callable[[Path, int], bytes],
        code_stats: Dict[str, Any],
    ) -> List[SkillProfileItem]:
        ev: List[Evidence] = []

        # language + config hints
        for p in fs_files:
            ext = p.suffix.lstrip(".").lower()
            lang = LANGUAGE_MAP.get(ext)
            if lang and lang in TAXONOMY:
                ev.append(self._ev(lang, "file_extension", str(p), str(p), 0.60))

            # known config names → hint
            base = p.name
            for rx, skill, src in KNOWN_CONFIG_HINTS:
                if rx.match(base):
                    ev.append(self._ev(skill, src, base, str(p), 0.70))

        # manifests
        ev += self._scan_package_json(fs_files, file_reader)
        ev += self._scan_requirements(fs_files, file_reader)
        ev += self._scan_pyproject(fs_files, file_reader)
        ev += self._scan_maven(fs_files, file_reader)
        ev += self._scan_gradle(fs_files, file_reader)
        ev += self._scan_go_cargo_csproj_composer(fs_files, file_reader)

        # snippets
        ev += self._scan_snippets(fs_files, file_reader)

        return self._merge(ev, code_stats)

    def _extract_projectfiles(
        self,
        wrapped_files: List[Tuple["_PseudoPath", Any]],
        get_bytes: Callable[[Any, int], bytes],
        code_stats: Dict[str, Any],
    ) -> List[SkillProfileItem]:
        ev: List[Evidence] = []

        # language + config hints
        for pseudo, obj in wrapped_files:
            ext = pseudo.suffix.lstrip(".").lower()
            lang = LANGUAGE_MAP.get(ext)
            if lang and lang in TAXONOMY:
                ev.append(self._ev(lang, "file_extension", pseudo.as_posix(), pseudo.as_posix(), 0.60))

            base = pseudo.name
            for rx, skill, src in KNOWN_CONFIG_HINTS:
                if rx.match(base):
                    ev.append(self._ev(skill, src, base, pseudo.as_posix(), 0.70))

        # manifests
        ev += self._scan_package_json_pf(wrapped_files, get_bytes)
        ev += self._scan_requirements_pf(wrapped_files, get_bytes)
        ev += self._scan_pyproject_pf(wrapped_files, get_bytes)
        ev += self._scan_maven_pf(wrapped_files, get_bytes)
        ev += self._scan_gradle_pf(wrapped_files, get_bytes)
        ev += self._scan_go_cargo_csproj_composer_pf(wrapped_files, get_bytes)

        # snippets
        ev += self._scan_snippets_pf(wrapped_files, get_bytes)

        return self._merge(ev, code_stats)

    # ---------- scanners for filesystem ----------

    def _scan_package_json(self, files: List[Path], reader) -> List[Evidence]:
        out: List[Evidence] = []
        for p in (f for f in files if f.name == "package.json"):
            data = _safe_json(p, reader)
            if not isinstance(data, dict):
                continue
            dep_maps = [data.get("dependencies") or {}, data.get("devDependencies") or {}]
            for deps in dep_maps:
                for name in deps.keys():
                    for rx, skill in DEP_TO_SKILL:
                        if rx.search(name):
                            out.append(self._ev(skill, "dependency", f"dep:{name}", str(p), 0.80))
            scripts = data.get("scripts") or {}
            for s in scripts.values():
                if "jest" in s:   out.append(self._ev("Jest", "test_framework", f"script:{s}", str(p), 0.70))
                if "vitest" in s: out.append(self._ev("Vitest","test_framework", f"script:{s}", str(p), 0.70))
                if "eslint" in s: out.append(self._ev("ESLint","linter_config", f"script:{s}", str(p), 0.65))
                if "prettier" in s: out.append(self._ev("Prettier","linter_config", f"script:{s}", str(p), 0.65))
                if "docker" in s: out.append(self._ev("Docker","build_tool", f"script:{s}", str(p), 0.60))
        return out

    def _scan_requirements(self, files: List[Path], reader) -> List[Evidence]:
        out: List[Evidence] = []
        for p in (f for f in files if re.match(r"requirements.*\.txt$", f.name)):
            text = _safe_text(p, reader)
            if not text:
                continue
            for rx, skill in DEP_TO_SKILL:
                if rx.search(text):
                    out.append(self._ev(skill, "dependency", f"requirements:{rx.pattern}", str(p), 0.80))
            if re.search(r"\bpytest\b", text, re.I):
                out.append(self._ev("PyTest", "test_framework", "requirements:pytest", str(p), 0.75))
        return out

    def _scan_pyproject(self, files: List[Path], reader) -> List[Evidence]:
        out: List[Evidence] = []
        for p in (f for f in files if f.name == "pyproject.toml"):
            text = _safe_text(p, reader)
            if not text: continue
            if re.search(r"\[tool\.poetry\]", text, re.I):
                out.append(self._ev("Poetry", "build_tool", "pyproject.toml", str(p), 0.70))
            for rx, skill in DEP_TO_SKILL:
                if rx.search(text):
                    out.append(self._ev(skill, "dependency", f"pyproject:{rx.pattern}", str(p), 0.75))
        return out

    def _scan_maven(self, files: List[Path], reader) -> List[Evidence]:
        out: List[Evidence] = []
        for p in (f for f in files if f.name.lower() == "pom.xml"):
            text = _safe_text(p, reader)
            if not text:
                continue
            low = text.lower()

            out.append(self._ev("Maven", "build_tool", "pom.xml", str(p), 0.70))

            if ("<groupid>org.springframework</groupid>" in low
                or re.search(r"<artifactid>\s*spring-[^<]+</artifactid>", low)):
                out.append(self._ev("Spring", "dependency", "pom.xml:spring", str(p), 0.85))

            if re.search(r"\bjunit\b", text, re.I):
                out.append(self._ev("JUnit", "test_framework", "pom.xml:junit", str(p), 0.75))
        return out

    def _scan_gradle(self, files: List[Path], reader) -> List[Evidence]:
        out: List[Evidence] = []
        for p in (f for f in files if f.name in ("build.gradle","build.gradle.kts")):
            text = _safe_text(p, reader)
            if not text: continue
            out.append(self._ev("Gradle", "build_tool", p.name, str(p), 0.75))
            if re.search(r"spring-boot", text, re.I):
                out.append(self._ev("Spring","dependency","gradle:spring-boot",str(p),0.80))
            if re.search(r"junit", text, re.I):
                out.append(self._ev("JUnit","test_framework","gradle:junit",str(p),0.70))
        return out

    def _scan_go_cargo_csproj_composer(self, files: List[Path], reader) -> List[Evidence]:
        out: List[Evidence] = []
        for p in (f for f in files if f.name == "go.mod"):
            out.append(self._ev("Go", "build_tool", "go.mod", str(p), 0.60))
        for p in (f for f in files if f.name == "Cargo.toml"):
            out.append(self._ev("Rust", "build_tool", "Cargo.toml", str(p), 0.60))
        for p in (f for f in files if f.suffix.lower() == ".csproj"):
            out.append(self._ev(".NET", "build_tool", p.name, str(p), 0.70))
            text = _safe_text(p, reader) or ""
            if re.search(r"Microsoft\.AspNet", text, re.I):
                out.append(self._ev("ASP.NET", "dependency", "csproj:aspnet", str(p), 0.80))
        for p in (f for f in files if f.name == "composer.json"):
            text = _safe_text(p, reader)
            if not text: continue
            for rx, skill in DEP_TO_SKILL:
                if rx.search(text):
                    out.append(self._ev(skill, "dependency", f"composer:{rx.pattern}", str(p), 0.75))
        return out

    def _scan_snippets(self, files: List[Path], reader) -> List[Evidence]:
        out: List[Evidence] = []
        for p in files:
            text = _safe_text(p, reader, limit=True)
            if text is None:
                continue
            for rx, skill, source in SNIPPET_PATTERNS:
                if rx.search(text):
                    out.append(self._ev(skill, source, f"{p.name}:{rx.pattern}", str(p), 0.70 if "import" in source else 0.55))
            if ("import" not in text) and re.search(r"\bdef\s+\w+\(.*\):", text):
                out.append(self._ev("Python","snippet_pattern", f"{p.name}:def", str(p), 0.55))
        return out

    # ---------- scanners for ProjectFolder (use get_bytes) ----------

    def _scan_package_json_pf(self, wrapped, get_bytes) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in (w for w in wrapped if w[0].name == "package.json"):
            data = _safe_json_pf(obj, get_bytes)
            if not isinstance(data, dict): continue
            dep_maps = [data.get("dependencies") or {}, data.get("devDependencies") or {}]
            for deps in dep_maps:
                for name in deps.keys():
                    for rx, skill in DEP_TO_SKILL:
                        if rx.search(name):
                            out.append(self._ev(skill,"dependency",f"dep:{name}",pseudo.as_posix(),0.80))
            scripts = data.get("scripts") or {}
            for s in scripts.values():
                if "jest" in s:   out.append(self._ev("Jest","test_framework",f"script:{s}",pseudo.as_posix(),0.70))
                if "vitest" in s: out.append(self._ev("Vitest","test_framework",f"script:{s}",pseudo.as_posix(),0.70))
                if "eslint" in s: out.append(self._ev("ESLint","linter_config",f"script:{s}",pseudo.as_posix(),0.65))
                if "prettier" in s: out.append(self._ev("Prettier","linter_config",f"script:{s}",pseudo.as_posix(),0.65))
                if "docker" in s: out.append(self._ev("Docker","build_tool",f"script:{s}",pseudo.as_posix(),0.60))
        return out

    def _scan_requirements_pf(self, wrapped, get_bytes) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in (w for w in wrapped if re.match(r"requirements.*\.txt$", w[0].name)):
            text = _safe_text_pf(obj, get_bytes)
            if not text: continue
            for rx, skill in DEP_TO_SKILL:
                if rx.search(text):
                    out.append(self._ev(skill,"dependency",f"requirements:{rx.pattern}",pseudo.as_posix(),0.80))
            if re.search(r"\bpytest\b", text, re.I):
                out.append(self._ev("PyTest","test_framework","requirements:pytest",pseudo.as_posix(),0.75))
        return out

    def _scan_pyproject_pf(self, wrapped, get_bytes) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in (w for w in wrapped if w[0].name == "pyproject.toml"):
            text = _safe_text_pf(obj, get_bytes)
            if not text: continue
            if re.search(r"\[tool\.poetry\]", text, re.I):
                out.append(self._ev("Poetry","build_tool","pyproject.toml",pseudo.as_posix(),0.70))
            for rx, skill in DEP_TO_SKILL:
                if rx.search(text):
                    out.append(self._ev(skill,"dependency",f"pyproject:{rx.pattern}",pseudo.as_posix(),0.75))
        return out

    def _scan_maven_pf(self, wrapped, get_bytes) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in (w for w in wrapped if w[0].name.lower() == "pom.xml"):
            text = _safe_text_pf(obj, get_bytes)
            if not text:
                continue

            low = text.lower()
            out.append(self._ev("Maven", "build_tool", "pom.xml", pseudo.as_posix(), 0.70))

            if (re.search(r"<\s*groupid\s*>\s*org\.springframework\s*<\s*/\s*groupid\s*>", low)
                or re.search(r"<\s*artifactid\s*>\s*spring-[^<]+<\s*/\s*artifactid\s*>", low)):
                out.append(self._ev("Spring", "dependency", "pom.xml:spring", pseudo.as_posix(), 0.85))

            if re.search(r"\bjunit\b", low):
                out.append(self._ev("JUnit", "test_framework", "pom.xml:junit", pseudo.as_posix(), 0.75))
            else:
                out.append(self._ev("JUnit", "heuristic", "pom.xml:assumed-test-framework", pseudo.as_posix(), 0.55))
        return out

    def _scan_gradle_pf(self, wrapped, get_bytes) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in (w for w in wrapped if w[0].name in ("build.gradle","build.gradle.kts")):
            text = _safe_text_pf(obj, get_bytes)
            if not text: continue
            out.append(self._ev("Gradle","build_tool",pseudo.name,pseudo.as_posix(),0.75))
            if re.search(r"spring-boot", text, re.I):
                out.append(self._ev("Spring","dependency","gradle:spring-boot",pseudo.as_posix(),0.80))
            if re.search(r"junit", text, re.I):
                out.append(self._ev("JUnit","test_framework","gradle:junit",pseudo.as_posix(),0.70))
        return out

    def _scan_go_cargo_csproj_composer_pf(self, wrapped, get_bytes) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in (w for w in wrapped if w[0].name == "go.mod"):
            out.append(self._ev("Go","build_tool","go.mod",pseudo.as_posix(),0.60))
        for pseudo, obj in (w for w in wrapped if w[0].name == "Cargo.toml"):
            out.append(self._ev("Rust","build_tool","Cargo.toml",pseudo.as_posix(),0.60))
        for pseudo, obj in ((a, b) for (a, b) in wrapped if a.suffix.lower() == ".csproj"):
            out.append(self._ev(".NET","build_tool",pseudo.name,pseudo.as_posix(),0.70))
            text = _safe_text_pf(obj, get_bytes) or ""
            if re.search(r"Microsoft\.AspNet", text, re.I):
                out.append(self._ev("ASP.NET","dependency","csproj:aspnet",pseudo.as_posix(),0.80))
        for pseudo, obj in (w for w in wrapped if w[0].name == "composer.json"):
            text = _safe_text_pf(obj, get_bytes)
            if not text: continue
            for rx, skill in DEP_TO_SKILL:
                if rx.search(text):
                    out.append(self._ev(skill,"dependency",f"composer:{rx.pattern}",pseudo.as_posix(),0.75))
        return out

    def _scan_snippets_pf(self, wrapped, get_bytes) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in wrapped:
            text = _safe_text_pf(obj, get_bytes, limit=True)
            if text is None: continue
            for rx, skill, source in SNIPPET_PATTERNS:
                if rx.search(text):
                    out.append(self._ev(skill, source, f"{pseudo.name}:{rx.pattern}", pseudo.as_posix(), 0.70 if "import" in source else 0.55))
            if ("import" not in text) and re.search(r"\bdef\s+\w+\(.*\):", text):
                out.append(self._ev("Python","snippet_pattern", f"{pseudo.name}:def", pseudo.as_posix(), 0.55))
        return out

    # ---------- merge & utils ----------

    def _merge(self, ev: List[Evidence], code_stats: Dict[str, Any]) -> List[SkillProfileItem]:
        bucket: Dict[str, SkillProfileItem] = {}
        for e in ev:
            if e.skill not in TAXONOMY:
                continue
            cur = bucket.get(e.skill)
            if not cur:
                bucket[e.skill] = SkillProfileItem(skill=e.skill, confidence=min(e.weight, 0.98), evidence=[e], proficiency=0.0)
            else:
                cur.confidence = min(cur.confidence + (1 - cur.confidence) * e.weight * 0.8, 0.98)
                cur.evidence.append(e)

        # small pair bonuses for common stacks
        def bump(a: str, b: str, bonus=0.03):
            if a in bucket and b in bucket:
                bucket[a].confidence = min(bucket[a].confidence + bonus, 0.98)
                bucket[b].confidence = min(bucket[b].confidence + bonus, 0.98)
        bump("Python","Django"); bump("Python","Flask"); bump("Python","FastAPI")
        bump("Java","Spring");   bump("C#","ASP.NET")
        bump("JavaScript","React"); bump("TypeScript","React")

        # --- NEW: compute proficiency per skill using collected code_stats + evidence ---
        for skill, item in bucket.items():
            item.proficiency = min(self._estimate_proficiency(skill, item.evidence, code_stats), 0.98)

        # sort by confidence (desc), then by skill name
        return sorted(bucket.values(), key=lambda x: (-x.confidence, x.skill))

    def _ev(self, skill: str, source: str, raw: str, file_path: Optional[str], weight: float) -> Evidence:
        return Evidence(skill=skill, source=source, raw=raw, file_path=file_path, weight=weight)

    # default filesystem head-reader
    def _default_fs_reader(self, path: Path, limit: int) -> bytes:
        try:
            with path.open("rb") as fh:
                return fh.read(limit)
        except Exception:
            return b""

    # ---------- proficiency helpers ----------

    def _collect_code_stats_fs(self, files: List[Path], reader: Callable[[Path, int], bytes]) -> Dict[str, Any]:
        """
        Collect lightweight per-language stats for proficiency.
        Only cheap regex scans; no full parsing or external tools.
        """
        stats: Dict[str, Any] = {
            "total_files": 0,
            "python": {
                "files": 0,
                "lines": 0,
                "defs": 0,
                "async_defs": 0,
                "classes": 0,
                "with_blocks": 0,
                "doc_quotes": 0,   # counts of triple quotes
                "type_arrows": 0,  # '->' returns
                "type_params": 0,  # ':' inside def params (approx)
                "test_files": 0,
            },
            "docker": {
                "dockerfiles": 0,
                "compose": 0,
                "multistage": 0,
                "healthcheck": 0,
            },
        }

        for p in files:
            stats["total_files"] += 1
            name = p.name.lower()
            ext = p.suffix.lower().lstrip(".")

            # Python
            if ext == "py":
                stats["python"]["files"] += 1
                try:
                    txt = self._safe_read_text_fs(p, reader)
                except Exception:
                    txt = ""
                if txt:
                    stats["python"]["lines"] += txt.count("\n") + 1
                    stats["python"]["defs"] += len(re.findall(r"^\s*def\s+\w+\s*\(", txt, re.M))
                    stats["python"]["async_defs"] += len(re.findall(r"^\s*async\s+def\s+\w+\s*\(", txt, re.M))
                    stats["python"]["classes"] += len(re.findall(r"^\s*class\s+\w+\s*[\(:]", txt, re.M))
                    stats["python"]["with_blocks"] += len(re.findall(r"^\s*with\s+", txt, re.M))
                    stats["python"]["doc_quotes"] += len(re.findall(r'("""|\'\'\')', txt))
                    # rough typing heuristics
                    stats["python"]["type_arrows"] += txt.count("->")
                    # count ':' inside def parameter lists (very approximate)
                    stats["python"]["type_params"] += len(re.findall(r"def\s+\w+\s*\(([^)]*:)+[^)]*\)", txt))

                if name.startswith("test_") or "/tests/" in str(p).replace("\\", "/"):
                    stats["python"]["test_files"] += 1

            # Docker
            if name == "dockerfile":
                stats["docker"]["dockerfiles"] += 1
                try:
                    txt = self._safe_read_text_fs(p, reader, limit=False)  # Dockerfiles are small; read fully
                except Exception:
                    txt = ""
                if txt:
                    # multi-stage build: multiple FROM or "as <name>"
                    if len(re.findall(r"^\s*from\s+", txt, re.I | re.M)) > 1 or re.search(r"\bas\s+\w+\b", txt, re.I):
                        stats["docker"]["multistage"] += 1
                    if re.search(r"^\s*healthcheck\b", txt, re.I | re.M):
                        stats["docker"]["healthcheck"] += 1

            if re.match(r"docker-compose\.(ya?ml|json)$", name):
                stats["docker"]["compose"] += 1

        return stats

    def _collect_code_stats_pf(self, wrapped: List[Tuple["_PseudoPath", Any]], get_bytes: Callable[[Any, int], bytes]) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "total_files": 0,
            "python": {
                "files": 0,
                "lines": 0,
                "defs": 0,
                "async_defs": 0,
                "classes": 0,
                "with_blocks": 0,
                "doc_quotes": 0,
                "type_arrows": 0,
                "type_params": 0,
                "test_files": 0,
            },
            "docker": {
                "dockerfiles": 0,
                "compose": 0,
                "multistage": 0,
                "healthcheck": 0,
            },
        }

        for pseudo, obj in wrapped:
            stats["total_files"] += 1
            name = pseudo.name.lower()
            ext = pseudo.suffix.lower().lstrip(".")

            if ext == "py":
                stats["python"]["files"] += 1
                try:
                    b = get_bytes(obj, 262_144)  # read up to 256KB
                    txt = b.decode("utf-8", errors="ignore")
                except Exception:
                    txt = ""
                if txt:
                    stats["python"]["lines"] += txt.count("\n") + 1
                    stats["python"]["defs"] += len(re.findall(r"^\s*def\s+\w+\s*\(", txt, re.M))
                    stats["python"]["async_defs"] += len(re.findall(r"^\s*async\s+def\s+\w+\s*\(", txt, re.M))
                    stats["python"]["classes"] += len(re.findall(r"^\s*class\s+\w+\s*[\(:]", txt, re.M))
                    stats["python"]["with_blocks"] += len(re.findall(r"^\s*with\s+", txt, re.M))
                    stats["python"]["doc_quotes"] += len(re.findall(r'("""|\'\'\')', txt))
                    stats["python"]["type_arrows"] += txt.count("->")
                    stats["python"]["type_params"] += len(re.findall(r"def\s+\w+\s*\(([^)]*:)+[^)]*\)", txt))

                if name.startswith("test_") or "/tests/" in pseudo.as_posix():
                    stats["python"]["test_files"] += 1

            if name == "dockerfile":
                stats["docker"]["dockerfiles"] += 1
                try:
                    b = get_bytes(obj, 131_072)
                    txt = b.decode("utf-8", errors="ignore")
                except Exception:
                    txt = ""
                if txt:
                    if len(re.findall(r"^\s*from\s+", txt, re.I | re.M)) > 1 or re.search(r"\bas\s+\w+\b", txt, re.I):
                        stats["docker"]["multistage"] += 1
                    if re.search(r"^\s*healthcheck\b", txt, re.I | re.M):
                        stats["docker"]["healthcheck"] += 1

            if re.match(r"docker-compose\.(ya?ml|json)$", name):
                stats["docker"]["compose"] += 1

        return stats

    def _safe_read_text_fs(self, p: Path, reader: Callable[[Path, int], bytes], limit: bool=False) -> str:
        try:
            b = reader(p, 4096 if limit else 262_144)
            return b.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _estimate_proficiency(self, skill: str, evidence: List[Evidence], stats: Dict[str, Any]) -> float:
        """
        Produce a heuristic 0..1 proficiency score per skill (capped at 0.98 by caller).
        - Languages (Python) use code metrics (defs/classes/typing/tests/docs).
        - Tools (Docker) use config sophistication (multistage/healthcheck/compose).
        - Frameworks get a presence-based baseline; can be extended similarly.
        The goal is robustness and zero external dependencies.
        """
        skill_low = skill.lower()

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

            # Normalize a handful of signals to 0..1
            # usage_depth: async + classes + context managers per KLOC
            kloc = lines / 1000.0
            usage_depth = _sigmoid((async_defs + classes + with_blocks) / max(1.0, kloc * 10.0))

            # typing: presence of annotations (very rough)
            typing_ratio = _clip01((type_arrows + type_params) / max(1, defs * 1.5))

            # docs: docstring density (approx: doc quotes / defs)
            doc_ratio = _clip01(doc_quotes / max(1, defs * 1.2))

            # testing: share of test files among python files
            test_ratio = _clip01(test_files / max(1, files))

            # composition (weighted)
            proficiency = (
                0.40 * usage_depth +
                0.25 * typing_ratio +
                0.20 * doc_ratio +
                0.15 * test_ratio
            )
            # small nudge if pytest was seen in evidence
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

            # Basic presence baseline
            base = 0.35 if dockerfiles or compose else 0.0
            # Advanced patterns boost
            advanced = 0.0
            if multistage:
                advanced += 0.25
            if healthcheck:
                advanced += 0.15
            if compose:
                advanced += 0.15

            # Light bonus if CI/CD skill or docker scripts present
            if any(e.source in ("build_tool","linter_config","test_framework") and e.skill in ("Docker","CI/CD") for e in evidence):
                advanced += 0.05

            return _clip01(base + advanced)

        # ---- Frameworks / libraries (quick baseline) ----
        # Until you add per-framework analyzers, give a conservative baseline
        # based on repeated evidence.
        framework_like = {
            "Django","Flask","FastAPI","React","Next.js","Angular","Vue","Svelte",
            "Spring",".NET","ASP.NET","Express","Unity","Unreal Engine",
        }
        if skill in framework_like:
            # count import_statement + framework_convention + dependency
            hits = 0
            for e in evidence:
                if e.skill == skill and e.source in ("import_statement","framework_convention","dependency"):
                    hits += 1
            # Normalize: 1 hit -> ~0.45, 2 hits -> ~0.62, 3+ hits -> ~0.75
            return [0.0, 0.45, 0.62, 0.75][min(3, hits)]

        # ---- Testing tools (PyTest/JUnit/Jest/etc.) ----
        if skill in {"PyTest","JUnit","Jest","Vitest","Cypress","Playwright"}:
            # If tests folders seen, raise; else minimal
            # We only implemented Python test file counting here
            py_tests = stats.get("python", {}).get("test_files", 0)
            if py_tests >= 3:
                return 0.72
            if py_tests >= 1:
                return 0.55
            # dependency/scripts present but no files found
            return 0.4 if any(e.source in ("dependency","test_framework") for e in evidence) else 0.2

        # ---- Databases / Cloud (presence-driven baseline) ----
        if skill in {"PostgreSQL","MySQL","SQLite","MongoDB","Redis","AWS","GCP","Azure","Firebase"}:
            # count hits in dependencies/configs; conservative baseline
            hits = sum(1 for e in evidence if e.skill == skill and e.source in ("dependency","build_tool","framework_convention"))
            return [0.0, 0.35, 0.5, 0.65][min(3, hits)]

        # default: mild baseline proportional to evidence variety
        distinct_sources = len({e.source for e in evidence if e.skill == skill})
        return [0.0, 0.3, 0.45, 0.6][min(3, distinct_sources)]


# ---------- helpers ----------

def _safe_text(p: Path, reader: Callable[[Path, int], bytes], limit: bool=False) -> Optional[str]:
    try:
        b = reader(p, 4096 if limit else 1_000_000)
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return None

def _safe_json(p: Path, reader) -> Optional[dict]:
    try:
        txt = _safe_text(p, reader)
        return json.loads(txt) if txt else None
    except Exception:
        return None

def _safe_text_pf(obj: Any, get_bytes: Callable[[Any, int], bytes], limit: bool=False) -> Optional[str]:
    try:
        b = get_bytes(obj, 4096 if limit else 1_000_000)
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return None

def _safe_json_pf(obj: Any, get_bytes) -> Optional[dict]:
    try:
        txt = _safe_text_pf(obj, get_bytes)
        return json.loads(txt) if txt else None
    except Exception:
        return None

def _sigmoid(x: float) -> float:
    # Gentle squashing for ratios; avoids over-penalizing small repos
    import math
    return 1.0 / (1.0 + math.exp(-3.0 * (x - 0.5)))  # centered ~0.5

def _clip01(x: float) -> float:
    return 0.0 if x < 0.0 else (1.0 if x > 1.0 else x)

class _PseudoPath:
    """Minimal Path-like for ProjectFile objects (name/suffix and display path)."""
    def __init__(self, path_like: str):
        self._p = str(path_like).replace("\\", "/")
        self.name = self._p.split("/")[-1]
        self.suffix = "." + self.name.split(".")[-1] if "." in self.name else ""
    def as_posix(self) -> str:
        return self._p
