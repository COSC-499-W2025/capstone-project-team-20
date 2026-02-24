from __future__ import annotations

from typing import Dict, List

from src.models.contributor_role import ContributorSignals, RoleInference, RoleID
from src.analyzers.contribution_analyzer import ContributionStats


class RoleInferenceAnalyzer:
    
    FRONTEND_CATS = {"frontend"}        
    BACKEND_CATS = {"backend"}
    QA_CATS = {"qa"}
    DOCS_CATS = {"docs"}
    DEVOPS_CATS = {"devops"} 

    def analyze(self, author_stats: Dict[str, ContributionStats]) -> Dict[str, RoleInference]:
        total_commits = sum(s.total_commits for s in author_stats.values()) or 1

        results: Dict[str, RoleInference] = {}
        for username, stats in author_stats.items():
            signals = ContributorSignals(
                username=username,
                commit_share=stats.total_commits / total_commits,
                category_summary={
                    # YAML-driven categories 
                    "contribution_by_category": dict(getattr(stats, "contribution_by_role_signal", {}) or {}),

                    "contribution_by_type": dict(stats.contribution_by_type),
                    "lines_added": stats.lines_added,
                    "lines_deleted": stats.lines_deleted,
                    "files_touched_count": len(stats.files_touched),
                },
                skills=set(), 
            )
            results[username] = self._infer(signals)

        return results

    def _sum_cats(self, cats: Dict[str, int], names: set) -> float:
        return float(sum(float(cats.get(k, 0)) for k in names))

    def _infer(self, s: ContributorSignals) -> RoleInference:
        cats = s.category_summary.get("contribution_by_category", {}) or {}

        backend = self._sum_cats(cats, self.BACKEND_CATS)
        frontend = self._sum_cats(cats, self.FRONTEND_CATS)
        devops = self._sum_cats(cats, self.DEVOPS_CATS)
        qa = self._sum_cats(cats, self.QA_CATS)
        docs = self._sum_cats(cats, self.DOCS_CATS)

        # Everything else counts as "other"
        used_keys = self.BACKEND_CATS | self.FRONTEND_CATS | self.DEVOPS_CATS | self.QA_CATS | self.DOCS_CATS
        other = float(sum(float(v) for k, v in cats.items() if k not in used_keys))

        total = backend + frontend + devops + qa + docs + other
        if total <= 0:
            return RoleInference(primary_role=RoleID.NONE, confidence=0.0)

        backend_r = backend / total
        frontend_r = frontend / total
        devops_r = devops / total
        qa_r = qa / total
        docs_r = docs / total

        # breadth = number of buckets with >= 10%
        bucket_ratios = {
            "backend": backend_r,
            "frontend": frontend_r,
            "devops": devops_r,
            "qa": qa_r,
            "docs": docs_r,
        }
        breadth = sum(1 for v in bucket_ratios.values() if v >= 0.10)

        evidence = {
            "backend_ratio": round(backend_r, 3),
            "frontend_ratio": round(frontend_r, 3),
            "devops_ratio": round(devops_r, 3),
            "qa_ratio": round(qa_r, 3),
            "docs_ratio": round(docs_r, 3),
            "commit_share": round(float(s.commit_share), 3),
            "breadth": float(breadth),
        }

        # Docs / QA are very "dominant" roles
        if docs_r >= 0.50:
            return RoleInference(primary_role=RoleID.DOCS, confidence=docs_r, evidence=evidence)

        if qa_r >= 0.35:
            return RoleInference(primary_role=RoleID.QA, confidence=qa_r, evidence=evidence)

        # DevOps: strong infra/config footprint
        if devops_r >= 0.35 and devops_r >= max(backend_r, frontend_r, qa_r, docs_r):
            return RoleInference(primary_role=RoleID.DEVOPS, confidence=devops_r, evidence=evidence)

        # Tech lead: make rare (high threshold)
        # - meaningful commit share
        # - broad contributions across areas
        # - not primarily docs/qa/devops
        if s.commit_share >= 0.30 and breadth >= 3 and max(docs_r, qa_r, devops_r) < 0.35:
            conf = min(1.0, 0.6 + (float(s.commit_share) - 0.30) * 1.0 + (breadth - 3) * 0.1)
            return RoleInference(primary_role=RoleID.TECH_LEAD, confidence=conf, evidence=evidence)

        # Fullstack: meaningful backend + frontend
        if backend_r >= 0.25 and frontend_r >= 0.25:
            conf = min(1.0, (backend_r + frontend_r))
            return RoleInference(primary_role=RoleID.FULLSTACK, confidence=conf, evidence=evidence)

        # Frontend / Backend dominance
        if frontend_r >= 0.45 and backend_r <= 0.20:
            return RoleInference(primary_role=RoleID.FRONTEND, confidence=frontend_r, evidence=evidence)

        if backend_r >= 0.45 and backend_r > frontend_r:
            return RoleInference(primary_role=RoleID.BACKEND, confidence=backend_r, evidence=evidence)

        # If nothing strong, pick the best of backend/frontend/devops/qa/docs but keep NONE if very weak
        best_role, best_ratio = max(
            [
                (RoleID.BACKEND, backend_r),
                (RoleID.FRONTEND, frontend_r),
                (RoleID.DEVOPS, devops_r),
                (RoleID.QA, qa_r),
                (RoleID.DOCS, docs_r),
            ],
            key=lambda x: x[1],
        )

        if best_ratio < 0.25:
            return RoleInference(primary_role=RoleID.NONE, confidence=best_ratio, evidence=evidence)

        return RoleInference(primary_role=best_role, confidence=best_ratio, evidence=evidence)
