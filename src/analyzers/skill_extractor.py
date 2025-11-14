# -*- coding: utf-8 -*-
"""
skill_extractor.py

SkillExtractor builds a ranked skill profile for a project directory or an
in-memory ProjectFolder tree.

Responsibilities
- Orchestrate:
  - code stats collection (CodeStatsCollector)
  - evidence generation (SkillEvidenceScanner)
  - proficiency scoring (ProficiencyEstimator)
- Merge Evidence into SkillProfileItem rows with confidence & proficiency.

What it detects
- Languages (via LANGUAGE_MAP file extensions + snippet patterns).
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
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from .skill_code_stats import CodeStatsCollector
from .skill_models import Evidence, SkillProfileItem, TAXONOMY
from .skill_proficiency import ProficiencyEstimator
from .skill_scanners import SkillEvidenceScanner


class SkillExtractor:
    """
    High-level façade that coordinates evidence gathering and scoring.
    """

    def __init__(self, read_limit_bytes: int = 4096):
        self.read_limit = read_limit_bytes
        self._stats_collector = CodeStatsCollector()
        self._scanner = SkillEvidenceScanner(read_limit_bytes=read_limit_bytes)
        self._prof = ProficiencyEstimator()

    # ---------- Mode A: analyze a normal filesystem directory ----------

    def extract_from_path(self, root_path: Path) -> List[SkillProfileItem]:
        """
        Walk a filesystem directory, collect evidence and stats, and emit
        a ranked skill profile.
        """
        files = [p for p in root_path.rglob("*") if p.is_file()]
        code_stats = self._stats_collector.collect_fs(files, self._default_fs_reader)
        evidence = self._scanner.scan_fs(files, self._default_fs_reader)
        return self._merge(evidence, code_stats)

    # ---------- Mode B: analyze an in-memory ProjectFolder tree ----------

    def extract_from_project_folder(
        self,
        root_folder: Any,
        get_path: Callable[[Any], str],
        get_bytes: Callable[[Any, int], bytes],
    ) -> List[SkillProfileItem]:
        """
        Traverse a ProjectFolder-style tree (children/subdir) and derive a
        skill profile based on virtual paths and get_bytes.
        """
        project_files: List[Any] = []
        stack = [root_folder]
        while stack:
            cur = stack.pop()
            for f in getattr(cur, "children", []) or []:
                project_files.append(f)
            for sub in getattr(cur, "subdir", []) or []:
                stack.append(sub)

        wrapped: List[Tuple[_PseudoPath, Any]] = []
        for f in project_files:
            p = get_path(f)
            wrapped.append((_PseudoPath(p), f))

        code_stats = self._stats_collector.collect_project_folder(wrapped, get_bytes)
        evidence = self._scanner.scan_project_folder(wrapped, get_bytes)
        return self._merge(evidence, code_stats)

    # ---------- merge & scoring ----------

    def _merge(self, ev: List[Evidence], code_stats: Dict[str, Any]) -> List[SkillProfileItem]:
        """
        Combine raw Evidence into per-skill aggregates with diminishing-return
        confidence and heuristic proficiency.
        """
        bucket: Dict[str, SkillProfileItem] = {}

        for e in ev:
            if e.skill not in TAXONOMY:
                continue
            cur = bucket.get(e.skill)
            if not cur:
                bucket[e.skill] = SkillProfileItem(
                    skill=e.skill,
                    confidence=min(e.weight, 0.98),
                    evidence=[e],
                    proficiency=0.0,
                )
            else:
                # diminishing returns: each new signal increases confidence but
                # never to 1.0, and is weighted by its own strength
                cur.confidence = min(
                    cur.confidence + (1 - cur.confidence) * e.weight * 0.8,
                    0.98,
                )
                cur.evidence.append(e)

        # small pair bonuses for common stacks (light framework robustness)
        def bump(a: str, b: str, bonus: float = 0.03) -> None:
            if a in bucket and b in bucket:
                bucket[a].confidence = min(bucket[a].confidence + bonus, 0.98)
                bucket[b].confidence = min(bucket[b].confidence + bonus, 0.98)

        # Python backends
        bump("Python", "Django")
        bump("Python", "Flask")
        bump("Python", "FastAPI")

        # Java / JVM
        bump("Java", "Spring")

        # .NET
        bump("C#", "ASP.NET")
        bump(".NET", "ASP.NET")

        # JS / TS frontends
        bump("JavaScript", "React")
        bump("TypeScript", "React")
        bump("React", "Next.js")
        bump("JavaScript", "Node.js")
        bump("TypeScript", "Node.js")
        bump("Node.js", "React")

        # compute proficiency per skill using collected code_stats + evidence
        for skill, item in bucket.items():
            item.proficiency = min(
                self._prof.estimate(skill, item.evidence, code_stats),
                0.98,
            )

        # sort by confidence (desc), then by skill name for stable output
        return sorted(bucket.values(), key=lambda x: (-x.confidence, x.skill))

    # ---------- low-level FS reader ----------

    def _default_fs_reader(self, path: Path, limit: int) -> bytes:
        try:
            with path.open("rb") as fh:
                return fh.read(limit)
        except Exception:
            return b""


class _PseudoPath:
    """Minimal Path-like for ProjectFile objects (name/suffix and display path)."""

    def __init__(self, path_like: str):
        self._p = str(path_like).replace("\\", "/")
        self.name = self._p.split("/")[-1]
        self.suffix = "." + self.name.split(".")[-1] if "." in self.name else ""

    def as_posix(self) -> str:
        return self._p
