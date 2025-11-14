"""
Evidence collection: scan files and project folders to produce raw Evidence events.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

from .language_detector import LANGUAGE_MAP
from .skill_models import Evidence, TAXONOMY
from .skill_patterns import DEP_TO_SKILL, SNIPPET_PATTERNS, KNOWN_CONFIG_HINTS


class SkillEvidenceScanner:
    def __init__(self, read_limit_bytes: int = 4096):
        self.read_limit = read_limit_bytes

    # ---------- public API ----------

    def scan_fs(self, fs_files: List[Path], reader: Callable[[Path, int], bytes]) -> List[Evidence]:
        ev: List[Evidence] = []

        # language + config hints
        for p in fs_files:
            ext = p.suffix.lstrip(".").lower()
            lang = LANGUAGE_MAP.get(ext)
            if lang and lang in TAXONOMY:
                ev.append(self._ev(lang, "file_extension", str(p), str(p), 0.60))

            base = p.name
            for rx, skill, src in KNOWN_CONFIG_HINTS:
                if rx.match(base):
                    ev.append(self._ev(skill, src, base, str(p), 0.70))

        # manifests
        ev += self._scan_package_json_fs(fs_files, reader)
        ev += self._scan_requirements_fs(fs_files, reader)
        ev += self._scan_pyproject_fs(fs_files, reader)
        ev += self._scan_maven_fs(fs_files, reader)
        ev += self._scan_gradle_fs(fs_files, reader)
        ev += self._scan_go_cargo_csproj_composer_fs(fs_files, reader)

        # snippets
        ev += self._scan_snippets_fs(fs_files, reader)

        return ev

    def scan_project_folder(
        self,
        wrapped_files: List[Tuple[Any, Any]],
        get_bytes: Callable[[Any, int], bytes],
    ) -> List[Evidence]:
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

        return ev

    # ---------- internal helpers ----------

    def _ev(self, skill: str, source: str, raw: str, file_path: str, weight: float) -> Evidence:
        return Evidence(skill=skill, source=source, raw=raw, file_path=file_path, weight=weight)

    # ---------- scanners for filesystem ----------

    def _scan_package_json_fs(self, files: List[Path], reader: Callable[[Path, int], bytes]) -> List[Evidence]:
        out: List[Evidence] = []
        for p in (f for f in files if f.name == "package.json"):
            data = _safe_json_fs(p, reader)
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
                if "jest" in s:
                    out.append(self._ev("Jest", "test_framework", f"script:{s}", str(p), 0.70))
                if "vitest" in s:
                    out.append(self._ev("Vitest", "test_framework", f"script:{s}", str(p), 0.70))
                if "eslint" in s:
                    out.append(self._ev("ESLint", "linter_config", f"script:{s}", str(p), 0.65))
                if "prettier" in s:
                    out.append(self._ev("Prettier", "linter_config", f"script:{s}", str(p), 0.65))
                if "docker" in s:
                    out.append(self._ev("Docker", "build_tool", f"script:{s}", str(p), 0.60))
        return out

    def _scan_requirements_fs(self, files: List[Path], reader: Callable[[Path, int], bytes]) -> List[Evidence]:
        out: List[Evidence] = []
        for p in (f for f in files if re.match(r"requirements.*\.txt$", f.name)):
            text = _safe_text_fs(p, reader)
            if not text:
                continue
            for rx, skill in DEP_TO_SKILL:
                if rx.search(text):
                    out.append(self._ev(skill, "dependency", f"requirements:{rx.pattern}", str(p), 0.80))
            if re.search(r"\bpytest\b", text, re.I):
                out.append(self._ev("PyTest", "test_framework", "requirements:pytest", str(p), 0.75))
        return out

    def _scan_pyproject_fs(self, files: List[Path], reader: Callable[[Path, int], bytes]) -> List[Evidence]:
        out: List[Evidence] = []
        for p in (f for f in files if f.name == "pyproject.toml"):
            text = _safe_text_fs(p, reader)
            if not text:
                continue
            if re.search(r"\[tool\.poetry\]", text, re.I):
                out.append(self._ev("Poetry", "build_tool", "pyproject.toml", str(p), 0.70))
            for rx, skill in DEP_TO_SKILL:
                if rx.search(text):
                    out.append(self._ev(skill, "dependency", f"pyproject:{rx.pattern}", str(p), 0.75))
        return out

    def _scan_maven_fs(self, files: List[Path], reader: Callable[[Path, int], bytes]) -> List[Evidence]:
        """
        Maven pipeline with defensive Spring/JUnit detection, aligned with PF path.
        """
        out: List[Evidence] = []
        for p in (f for f in files if f.name.lower() == "pom.xml"):
            text = _safe_text_fs(p, reader)
            if not text:
                continue

            low = text.lower()
            out.append(self._ev("Maven", "build_tool", "pom.xml", str(p), 0.70))

            if (
                re.search(r"<\s*groupid\s*>\s*org\.springframework\s*<\s*/\s*groupid\s*>", low)
                or re.search(r"<\s*artifactid\s*>\s*spring-[^<]+<\s*/\s*artifactid\s*>", low)
            ):
                out.append(self._ev("Spring", "dependency", "pom.xml:spring", str(p), 0.85))

            if re.search(r"\bjunit\b", low):
                out.append(self._ev("JUnit", "test_framework", "pom.xml:junit", str(p), 0.75))
            else:
                out.append(
                    self._ev(
                        "JUnit",
                        "heuristic",
                        "pom.xml:assumed-test-framework",
                        str(p),
                        0.55,
                    )
                )
        return out

    def _scan_gradle_fs(self, files: List[Path], reader: Callable[[Path, int], bytes]) -> List[Evidence]:
        out: List[Evidence] = []
        for p in (f for f in files if f.name in ("build.gradle", "build.gradle.kts")):
            text = _safe_text_fs(p, reader)
            if not text:
                continue
            out.append(self._ev("Gradle", "build_tool", p.name, str(p), 0.75))
            if re.search(r"spring-boot", text, re.I):
                out.append(self._ev("Spring", "dependency", "gradle:spring-boot", str(p), 0.80))
            if re.search(r"junit", text, re.I):
                out.append(self._ev("JUnit", "test_framework", "gradle:junit", str(p), 0.70))
        return out

    def _scan_go_cargo_csproj_composer_fs(
        self,
        files: List[Path],
        reader: Callable[[Path, int], bytes],
    ) -> List[Evidence]:
        out: List[Evidence] = []
        for p in (f for f in files if f.name == "go.mod"):
            out.append(self._ev("Go", "build_tool", "go.mod", str(p), 0.60))
        for p in (f for f in files if f.name == "Cargo.toml"):
            out.append(self._ev("Rust", "build_tool", "Cargo.toml", str(p), 0.60))
        for p in (f for f in files if f.suffix.lower() == ".csproj"):
            out.append(self._ev(".NET", "build_tool", p.name, str(p), 0.70))
            text = _safe_text_fs(p, reader) or ""
            if re.search(r"Microsoft\.AspNet", text, re.I):
                out.append(self._ev("ASP.NET", "dependency", "csproj:aspnet", str(p), 0.80))
        for p in (f for f in files if f.name == "composer.json"):
            text = _safe_text_fs(p, reader)
            if not text:
                continue
            for rx, skill in DEP_TO_SKILL:
                if rx.search(text):
                    out.append(self._ev(skill, "dependency", f"composer:{rx.pattern}", str(p), 0.75))
        return out

    def _scan_snippets_fs(self, files: List[Path], reader: Callable[[Path, int], bytes]) -> List[Evidence]:
        out: List[Evidence] = []
        for p in files:
            text = _safe_text_fs(p, reader, limit=True)
            if text is None:
                continue
            for rx, skill, source in SNIPPET_PATTERNS:
                if rx.search(text):
                    out.append(
                        self._ev(
                            skill,
                            source,
                            f"{p.name}:{rx.pattern}",
                            str(p),
                            0.70 if "import" in source else 0.55,
                        )
                    )
            if ("import" not in text) and re.search(r"\bdef\s+\w+\(.*\):", text):
                out.append(self._ev("Python", "snippet_pattern", f"{p.name}:def", str(p), 0.55))
        return out

    # ---------- scanners for ProjectFolder ----------

    def _scan_package_json_pf(
        self,
        wrapped: List[Tuple[Any, Any]],
        get_bytes: Callable[[Any, int], bytes],
    ) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in (w for w in wrapped if w[0].name == "package.json"):
            data = _safe_json_pf(obj, get_bytes)
            if not isinstance(data, dict):
                continue
            dep_maps = [data.get("dependencies") or {}, data.get("devDependencies") or {}]
            for deps in dep_maps:
                for name in deps.keys():
                    for rx, skill in DEP_TO_SKILL:
                        if rx.search(name):
                            out.append(self._ev(skill, "dependency", f"dep:{name}", pseudo.as_posix(), 0.80))
            scripts = data.get("scripts") or {}
            for s in scripts.values():
                if "jest" in s:
                    out.append(self._ev("Jest", "test_framework", f"script:{s}", pseudo.as_posix(), 0.70))
                if "vitest" in s:
                    out.append(self._ev("Vitest", "test_framework", f"script:{s}", pseudo.as_posix(), 0.70))
                if "eslint" in s:
                    out.append(self._ev("ESLint", "linter_config", f"script:{s}", pseudo.as_posix(), 0.65))
                if "prettier" in s:
                    out.append(self._ev("Prettier", "linter_config", f"script:{s}", pseudo.as_posix(), 0.65))
                if "docker" in s:
                    out.append(self._ev("Docker", "build_tool", f"script:{s}", pseudo.as_posix(), 0.60))
        return out

    def _scan_requirements_pf(
        self,
        wrapped: List[Tuple[Any, Any]],
        get_bytes: Callable[[Any, int], bytes],
    ) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in (w for w in wrapped if re.match(r"requirements.*\.txt$", w[0].name)):
            text = _safe_text_pf(obj, get_bytes)
            if not text:
                continue
            for rx, skill in DEP_TO_SKILL:
                if rx.search(text):
                    out.append(self._ev(skill, "dependency", f"requirements:{rx.pattern}", pseudo.as_posix(), 0.80))
            if re.search(r"\bpytest\b", text, re.I):
                out.append(self._ev("PyTest", "test_framework", "requirements:pytest", pseudo.as_posix(), 0.75))
        return out

    def _scan_pyproject_pf(
        self,
        wrapped: List[Tuple[Any, Any]],
        get_bytes: Callable[[Any, int], bytes],
    ) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in (w for w in wrapped if w[0].name == "pyproject.toml"):
            text = _safe_text_pf(obj, get_bytes)
            if not text:
                continue
            if re.search(r"\[tool\.poetry\]", text, re.I):
                out.append(self._ev("Poetry", "build_tool", "pyproject.toml", pseudo.as_posix(), 0.70))
            for rx, skill in DEP_TO_SKILL:
                if rx.search(text):
                    out.append(self._ev(skill, "dependency", f"pyproject:{rx.pattern}", pseudo.as_posix(), 0.75))
        return out

    def _scan_maven_pf(
        self,
        wrapped: List[Tuple[Any, Any]],
        get_bytes: Callable[[Any, int], bytes],
    ) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in (w for w in wrapped if w[0].name.lower() == "pom.xml"):
            text = _safe_text_pf(obj, get_bytes)
            if not text:
                continue

            low = text.lower()
            out.append(self._ev("Maven", "build_tool", "pom.xml", pseudo.as_posix(), 0.70))

            if (
                re.search(r"<\s*groupid\s*>\s*org\.springframework\s*<\s*/\s*groupid\s*>", low)
                or re.search(r"<\s*artifactid\s*>\s*spring-[^<]+<\s*/\s*artifactid\s*>", low)
            ):
                out.append(self._ev("Spring", "dependency", "pom.xml:spring", pseudo.as_posix(), 0.85))

            if re.search(r"\bjunit\b", low):
                out.append(self._ev("JUnit", "test_framework", "pom.xml:junit", pseudo.as_posix(), 0.75))
            else:
                out.append(
                    self._ev(
                        "JUnit",
                        "heuristic",
                        "pom.xml:assumed-test-framework",
                        pseudo.as_posix(),
                        0.55,
                    )
                )
        return out

    def _scan_gradle_pf(
        self,
        wrapped: List[Tuple[Any, Any]],
        get_bytes: Callable[[Any, int], bytes],
    ) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in (w for w in wrapped if w[0].name in ("build.gradle", "build.gradle.kts")):
            text = _safe_text_pf(obj, get_bytes)
            if not text:
                continue
            out.append(self._ev("Gradle", "build_tool", pseudo.name, pseudo.as_posix(), 0.75))
            if re.search(r"spring-boot", text, re.I):
                out.append(self._ev("Spring", "dependency", "gradle:spring-boot", pseudo.as_posix(), 0.80))
            if re.search(r"junit", text, re.I):
                out.append(self._ev("JUnit", "test_framework", "gradle:junit", pseudo.as_posix(), 0.70))
        return out

    def _scan_go_cargo_csproj_composer_pf(
        self,
        wrapped: List[Tuple[Any, Any]],
        get_bytes: Callable[[Any, int], bytes],
    ) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in (w for w in wrapped if w[0].name == "go.mod"):
            out.append(self._ev("Go", "build_tool", "go.mod", pseudo.as_posix(), 0.60))
        for pseudo, obj in (w for w in wrapped if w[0].name == "Cargo.toml"):
            out.append(self._ev("Rust", "build_tool", "Cargo.toml", pseudo.as_posix(), 0.60))
        for pseudo, obj in ((a, b) for (a, b) in wrapped if a.suffix.lower() == ".csproj"):
            out.append(self._ev(".NET", "build_tool", pseudo.name, pseudo.as_posix(), 0.70))
            text = _safe_text_pf(obj, get_bytes) or ""
            if re.search(r"Microsoft\.AspNet", text, re.I):
                out.append(self._ev("ASP.NET", "dependency", "csproj:aspnet", pseudo.as_posix(), 0.80))
        for pseudo, obj in (w for w in wrapped if w[0].name == "composer.json"):
            text = _safe_text_pf(obj, get_bytes)
            if not text:
                continue
            for rx, skill in DEP_TO_SKILL:
                if rx.search(text):
                    out.append(self._ev(skill, "dependency", f"composer:{rx.pattern}", pseudo.as_posix(), 0.75))
        return out

    def _scan_snippets_pf(
        self,
        wrapped: List[Tuple[Any, Any]],
        get_bytes: Callable[[Any, int], bytes],
    ) -> List[Evidence]:
        out: List[Evidence] = []
        for pseudo, obj in wrapped:
            text = _safe_text_pf(obj, get_bytes, limit=True)
            if text is None:
                continue
            for rx, skill, source in SNIPPET_PATTERNS:
                if rx.search(text):
                    out.append(
                        self._ev(
                            skill,
                            source,
                            f"{pseudo.name}:{rx.pattern}",
                            pseudo.as_posix(),
                            0.70 if "import" in source else 0.55,
                        )
                    )
            if ("import" not in text) and re.search(r"\bdef\s+\w+\(.*\):", text):
                out.append(
                    self._ev(
                        "Python",
                        "snippet_pattern",
                        f"{pseudo.name}:def",
                        pseudo.as_posix(),
                        0.55,
                    )
                )
        return out


# ---------- helpers ----------

def _safe_text_fs(
    p: Path,
    reader: Callable[[Path, int], bytes],
    limit: bool = False,
) -> Optional[str]:
    try:
        b = reader(p, 4096 if limit else 1_000_000)
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _safe_json_fs(p: Path, reader: Callable[[Path, int], bytes]) -> Optional[dict]:
    try:
        txt = _safe_text_fs(p, reader)
        return json.loads(txt) if txt else None
    except Exception:
        return None


def _safe_text_pf(
    obj: Any,
    get_bytes: Callable[[Any, int], bytes],
    limit: bool = False,
) -> Optional[str]:
    try:
        b = get_bytes(obj, 4096 if limit else 1_000_000)
        return b.decode("utf-8", errors="ignore")
    except Exception:
        return None


def _safe_json_pf(obj: Any, get_bytes: Callable[[Any, int], bytes]) -> Optional[dict]:
    try:
        txt = _safe_text_pf(obj, get_bytes)
        return json.loads(txt) if txt else None
    except Exception:
        return None
