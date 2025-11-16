"""
Lightweight per-language code statistics used for proficiency scoring.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple


class CodeStatsCollector:
    def collect_fs(self, files: List[Path], reader: Callable[[Path, int], bytes]) -> Dict[str, Any]:
        """
        Collect lightweight per-language stats for proficiency.
        Mirrors the original _collect_code_stats_fs implementation.
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
                    stats["python"]["type_arrows"] += txt.count("->")
                    stats["python"]["type_params"] += len(
                        re.findall(r"def\s+\w+\s*\(([^)]*:)+[^)]*\)", txt)
                    )

                if name.startswith("test_") or "/tests/" in str(p).replace("\\", "/"):
                    stats["python"]["test_files"] += 1

            # Docker
            if name == "dockerfile":
                stats["docker"]["dockerfiles"] += 1
                try:
                    txt = self._safe_read_text_fs(p, reader, limit=False)
                except Exception:
                    txt = ""
                if txt:
                    if len(re.findall(r"^\s*from\s+", txt, re.I | re.M)) > 1 or re.search(
                        r"\bas\s+\w+\b", txt, re.I
                    ):
                        stats["docker"]["multistage"] += 1
                    if re.search(r"^\s*healthcheck\b", txt, re.I | re.M):
                        stats["docker"]["healthcheck"] += 1

            if re.match(r"docker-compose\.(ya?ml|json)$", name):
                stats["docker"]["compose"] += 1

        return stats

    def collect_project_folder(
        self,
        wrapped: List[Tuple[Any, Any]],
        get_bytes: Callable[[Any, int], bytes],
    ) -> Dict[str, Any]:
        """
        Same as collect_fs but works on in-memory ProjectFolder representation.
        `wrapped` is a list of (pseudo_path, file_obj) tuples.
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
                    b = get_bytes(obj, 262_144)
                    txt = b.decode("utf-8", errors="ignore")
                except Exception:
                    txt = ""
                if txt:
                    stats["python"]["lines"] += txt.count("\n") + 1
                    stats["python"]["defs"] += len(re.findall(r"^\s*def\s+\w+\s*\(", txt, re.M))
                    stats["python"]["async_defs"] += len(
                        re.findall(r"^\s*async\s+def\s+\w+\s*\(", txt, re.M)
                    )
                    stats["python"]["classes"] += len(
                        re.findall(r"^\s*class\s+\w+\s*[\(:]", txt, re.M)
                    )
                    stats["python"]["with_blocks"] += len(
                        re.findall(r"^\s*with\s+", txt, re.M)
                    )
                    stats["python"]["doc_quotes"] += len(
                        re.findall(r'("""|\'\'\')', txt)
                    )
                    stats["python"]["type_arrows"] += txt.count("->")
                    stats["python"]["type_params"] += len(
                        re.findall(r"def\s+\w+\s*\(([^)]*:)+[^)]*\)", txt)
                    )

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
                    if len(re.findall(r"^\s*from\s+", txt, re.I | re.M)) > 1 or re.search(
                        r"\bas\s+\w+\b", txt, re.I
                    ):
                        stats["docker"]["multistage"] += 1
                    if re.search(r"^\s*healthcheck\b", txt, re.I | re.M):
                        stats["docker"]["healthcheck"] += 1

            if re.match(r"docker-compose\.(ya?ml|json)$", name):
                stats["docker"]["compose"] += 1

        return stats

    def _safe_read_text_fs(self, p: Path, reader: Callable[[Path, int], bytes], limit: bool = False) -> str:
        try:
            b = reader(p, 4096 if limit else 262_144)
            return b.decode("utf-8", errors="ignore")
        except Exception:
            return ""
