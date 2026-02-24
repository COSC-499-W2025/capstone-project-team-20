import pytest

from src.analyzers.role_inference_analyzer import RoleInferenceAnalyzer
from src.models.contributor_role import ContributorSignals, RoleID
from src.analyzers.contribution_analyzer import ContributionStats


def _signals(
    *,
    commit_share: float = 0.0,
    role_lines: dict[str, int] | None = None,
) -> ContributorSignals:
    """
    Build ContributorSignals in the same shape RoleInferenceAnalyzer expects.
    role_lines are the role buckets (frontend/backend/devops/qa/docs) that come
    from ContributionStats.contribution_by_role_signal.
    """
    return ContributorSignals(
        username="u",
        commit_share=commit_share,
        category_summary={
            "contribution_by_category": dict(role_lines or {}),
            "contribution_by_type": {},
            "lines_added": 0,
            "lines_deleted": 0,
            "files_touched_count": 0,
        },
        skills=set(),
    )


def test_infer_returns_none_when_no_counts():
    a = RoleInferenceAnalyzer()
    res = a._infer(_signals(role_lines={}))
    assert res.primary_role == RoleID.NONE
    assert res.confidence == 0.0


def test_docs_dominant():
    a = RoleInferenceAnalyzer()
    # docs >= 0.50 should win immediately
    res = a._infer(_signals(role_lines={"docs": 60, "backend": 40}))
    assert res.primary_role == RoleID.DOCS
    assert res.confidence == pytest.approx(0.6, abs=1e-6)


def test_qa_dominant():
    a = RoleInferenceAnalyzer()
    # qa >= 0.35 should win (if docs not >= 0.50)
    res = a._infer(_signals(role_lines={"qa": 35, "backend": 65}))
    assert res.primary_role == RoleID.QA
    assert res.confidence == pytest.approx(0.35, abs=1e-6)


def test_devops_dominant_and_is_max():
    a = RoleInferenceAnalyzer()
    # devops must be >= 0.35 AND >= max(other ratios)
    res = a._infer(_signals(role_lines={"devops": 40, "backend": 30, "frontend": 30}))
    assert res.primary_role == RoleID.DEVOPS
    assert res.confidence == pytest.approx(0.4, abs=1e-6)


def test_tech_lead_rule_triggers():
    a = RoleInferenceAnalyzer()
    # commit_share >= 0.30, breadth >= 3, and docs/qa/devops < 0.35
    # breadth computed on backend/frontend/devops/qa/docs ratios >= 0.10
    res = a._infer(
        _signals(
            commit_share=0.30,
            role_lines={"backend": 40, "frontend": 40, "devops": 20},  # breadth = 3
        )
    )
    assert res.primary_role == RoleID.TECH_LEAD
    assert res.confidence >= 0.6  # baseline in your formula


def test_fullstack_rule_triggers_when_backend_and_frontend_both_meaningful():
    a = RoleInferenceAnalyzer()
    res = a._infer(_signals(role_lines={"backend": 30, "frontend": 30, "docs": 40}))
    # docs is 0.40 (<0.50), so it won't override; backend & frontend >= 0.25 => FULLSTACK
    assert res.primary_role == RoleID.FULLSTACK
    assert res.confidence == pytest.approx(0.60, abs=1e-6)


def test_frontend_dominance():
    a = RoleInferenceAnalyzer()
    res = a._infer(_signals(role_lines={"frontend": 70, "backend": 20, "devops": 10}))
    assert res.primary_role == RoleID.FRONTEND
    assert res.confidence == pytest.approx(0.70, abs=1e-6)


def test_backend_dominance():
    a = RoleInferenceAnalyzer()
    res = a._infer(_signals(role_lines={"backend": 70, "frontend": 20, "docs": 10}))
    assert res.primary_role == RoleID.BACKEND
    assert res.confidence == pytest.approx(0.70, abs=1e-6)


def test_best_ratio_below_threshold_returns_none():
    a = RoleInferenceAnalyzer()
    # best is backend at 0.24 => NONE (< 0.25)
    res = a._infer(_signals(role_lines={"backend": 24, "frontend": 23, "devops": 23, "qa": 15, "docs": 15}))
    assert res.primary_role == RoleID.NONE
    assert res.confidence == pytest.approx(0.24, abs=1e-6)


def test_analyze_uses_contribution_by_role_signal_and_commit_share():
    a = RoleInferenceAnalyzer()

    s1 = ContributionStats()
    s1.total_commits = 3
    s1.contribution_by_role_signal = {"docs": 60, "backend": 40}  # docs dominant => DOCS

    s2 = ContributionStats()
    s2.total_commits = 1
    s2.contribution_by_role_signal = {"backend": 80, "frontend": 20}  # backend dominant => BACKEND

    results = a.analyze({"alice": s1, "bob": s2})

    assert results["alice"].primary_role == RoleID.DOCS
    assert results["bob"].primary_role == RoleID.BACKEND

    # total commits = 4 => alice share 0.75, bob share 0.25 (evidence stores rounded commit_share)
    assert results["alice"].evidence["commit_share"] == pytest.approx(0.75, abs=1e-6)
    assert results["bob"].evidence["commit_share"] == pytest.approx(0.25, abs=1e-6)