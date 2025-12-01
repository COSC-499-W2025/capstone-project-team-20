from src.analyzers.badge_engine import (
    ProjectAnalyticsSnapshot,
    assign_badges,
    build_fun_facts,
    aggregate_badges,
)


def _snapshot(**overrides):
    base = dict(
        name="demo",
        total_files=100,
        total_size_kb=1024.0,
        total_size_mb=1.0,
        duration_days=10,
        category_summary={},
        languages={"Python": 1.0},
        skills=set(),
        author_count=1,
        collaboration_status="individual",
    )
    base.update(overrides)
    return ProjectAnalyticsSnapshot(**base)


def test_size_and_duration_badges():
    snap = _snapshot(total_size_mb=1500.0, duration_days=400)
    badges = assign_badges(snap)
    assert "gigantana" in badges
    assert "slow_burn" in badges


def test_language_diversity_badges():
    snap = _snapshot(
        languages={"Python": 0.4, "JavaScript": 0.3, "Go": 0.3}
    )
    badges = assign_badges(snap)
    assert "polyglot" in badges or "jack_of_all_trades" in badges


def test_collaboration_badges():
    solo = assign_badges(_snapshot(author_count=1))
    team = assign_badges(_snapshot(author_count=4, collaboration_status="collaborative"))
    assert "solo_runner" in solo
    assert "team_effort" in team


def test_category_badges():
    snap = _snapshot(
        category_summary={
            "test": {"file_share": 0.2},
            "docs": {"file_share": 0.25},
            "data": {"file_share": 0.3},
            "code": {"file_share": 0.7},
        }
    )
    badges = assign_badges(snap)
    assert "test_pilot" in badges
    assert "docs_guardian" in badges
    assert "data_wrangler" in badges
    assert "code_cruncher" in badges


def test_fun_facts_and_aggregate():
    snap = _snapshot(
        total_size_mb=2000.0,
        duration_days=42,
        languages={"Python": 0.5, "JavaScript": 0.5},
        author_count=3,
        collaboration_status="collaborative",
    )
    badges = assign_badges(snap)
    facts = build_fun_facts(snap, badges)

    # Basic sanity checks
    assert any("2000.0" in f or "2000" in f for f in facts)
    assert any("42" in f for f in facts)

    class P:
        def __init__(self, badges):
            self.badges = badges

    projects = [P(badges), P(["solo_runner"])]
    totals = aggregate_badges(projects)

    # With author_count=3, the first project gets "team_effort", not "solo_runner"
    assert totals["solo_runner"] == 1
    assert totals["team_effort"] == 1

