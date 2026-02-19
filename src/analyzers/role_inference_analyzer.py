from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from src.models.contributor_role import ContributorSignals, RoleInference, RoleID
from src.analyzers.contribution_analyzer import ContributionStats  # adjust import path


class RoleInferenceAnalyzer:
    def analyze(self, author_stats: Dict[str, ContributionStats]) -> Dict[str, RoleInference]:
        total_commits = sum(s.total_commits for s in author_stats.values()) or 1

        results: Dict[str, RoleInference] = {}
        for username, stats in author_stats.items():
            signals = ContributorSignals(
                username=username,
                commit_share=stats.total_commits / total_commits,
                category_summary={
                    "contribution_by_type": dict(stats.contribution_by_type),
                    "lines_added": stats.lines_added,
                    "lines_deleted": stats.lines_deleted,
                    "files_touched_count": len(stats.files_touched),
                },
                skills=set(),  # fill later if/when you have per-user skills
            )
            results[username] = self._infer(signals)

        return results

    def _infer(self, s: ContributorSignals) -> RoleInference:
        cbt = s.category_summary.get("contribution_by_type", {}) or {}
        code = float(cbt.get("code", 0))
        docs = float(cbt.get("docs", 0))
        test = float(cbt.get("test", 0))
        other = float(cbt.get("other", 0))
        total = code + docs + test + other

        # Avoid divide by zero
        if total <= 0:
            return RoleInference(primary_role=RoleID.NONE, confidence=0.0)

        docs_ratio = docs / total
        test_ratio = test / total
        code_ratio = code / total

        evidence = {
            "docs_ratio": round(docs_ratio, 3),
            "test_ratio": round(test_ratio, 3),
            "code_ratio": round(code_ratio, 3),
            "commit_share": round(float(s.commit_share), 3),
        }

        # Conservative MVP rules:
        if docs_ratio >= 0.50:
            return RoleInference(primary_role=RoleID.DOCS, confidence=docs_ratio, evidence=evidence)

        if test_ratio >= 0.35:
            return RoleInference(primary_role=RoleID.QA, confidence=test_ratio, evidence=evidence)

        # Tech lead (very conservative): high commit share + meaningful breadth (proxy with code_ratio)
        if s.commit_share >= 0.30 and code_ratio >= 0.40:
            return RoleInference(primary_role=RoleID.TECH_LEAD, confidence=min(1.0, s.commit_share + 0.2), evidence=evidence)

        return RoleInference(primary_role=RoleID.NONE, confidence=max(code_ratio, test_ratio, docs_ratio), evidence=evidence)
