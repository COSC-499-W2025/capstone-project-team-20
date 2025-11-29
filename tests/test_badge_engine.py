# tests/test_badge_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Set, Iterable
import sys
from pathlib import Path

# Ensure src/ is on sys.path
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from src.analyzers.badge_engine import (
    ProjectAnalyticsSnapshot,
    assign_badges,
    build_fun_facts,
    aggregate_badges,
)


def make_snapshot(
    *,
    name: str = "project",
    total_files: int = 0,
    total_size_mb: float = 0.0,
    duration_days: int = 0,
    category_summary: Dict[str, Dict[str, Any]] | None = None,
    languages: Dict[str, float] | None = None,
    skills: Set[str] | None = None,
    author_count: int = 1,
    collaboration_status: str = "individual",
    total_size_kb: float = 0.0,
) -> ProjectAnalyticsSnapshot:
    """
    Helper to build snapshots with sensible defaults.
    Only the arguments you care about need to be passed in.
    """
    return ProjectAnalyticsSnapshot(
        name=name,
        total_files=total_files,
        total_size_kb=total_size_kb,
        total_size_mb=total_size_mb,
        duration_days=duration_days,
        category_summary=category_summary or {},
        languages=languages or {},
        skills=skills or set(),
        author_count=author_count,
        collaboration_status=collaboration_status,
    )


# ---------------------------------------------------------------------------
# assign_badges: size / duration / language / collaboration
# ---------------------------------------------------------------------------


def test_badges_size_and_duration_and_solo_runner():
    snap = make_snapshot(
        total_files=100,
        total_size_mb=2048.0,  # >= 1024 → gigantana
        duration_days=400,     # >= 365 → slow_burn
        author_count=1,
        collaboration_status="individual",
    )

    badges = assign_badges(snap)

    assert "gigantana" in badges
    assert "slow_burn" in badges
    # single author
    assert "solo_runner" in badges


def test_badges_flash_build_and_fresh_breeze():
    snap = make_snapshot(
        total_files=25,
        total_size_mb=10.0,
        duration_days=5,  # <= 7 and files >= 20 → flash_build
    )

    badges = assign_badges(snap)

    assert "flash_build" in badges
    # duration <= 30 and files < 50 → fresh_breeze
    assert "fresh_breeze" in badges


def test_badges_language_diversity_polyglot_and_jack_of_all_trades():
    # 3 languages → polyglot
    snap_polyglot = make_snapshot(
        languages={"Python": 50.0, "JavaScript": 25.0, "C++": 25.0}
    )
    badges_polyglot = assign_badges(snap_polyglot)
    assert "polyglot" in badges_polyglot
    assert "jack_of_all_trades" not in badges_polyglot

    # 5 languages → jack_of_all_trades
    snap_joat = make_snapshot(
        languages={"Python": 20.0, "JavaScript": 20.0, "C++": 20.0, "Go": 20.0, "Rust": 20.0}
    )
    badges_joat = assign_badges(snap_joat)
    assert "jack_of_all_trades" in badges_joat


def test_badges_team_effort_for_multiple_authors():
    snap = make_snapshot(
        author_count=4,
        collaboration_status="collaborative",
    )
    badges = assign_badges(snap)
    assert "team_effort" in badges
    assert "solo_runner" not in badges


# ---------------------------------------------------------------------------
# assign_badges: category-driven and skill-driven
# ---------------------------------------------------------------------------


def test_badges_category_shares():
    # Use different keys to exercise _cat_metric fallback behaviour
    category_summary = {
        "code": {"files_pct": 0.7},
        "test": {"file_share": 0.2},
        "docs": {"share": 0.25},
        "design": {"file_share": 0.3},
        "data": {"file_share": 0.3},
        "game": {"file_share": 0.4},
    }

    snap = make_snapshot(
        total_files=100,
        total_size_mb=50.0,
        duration_days=50,
        category_summary=category_summary,
    )

    badges = assign_badges(snap)

    assert "code_cruncher" in badges
    assert "test_pilot" in badges
    assert "docs_guardian" in badges
    # design_share >= 0.25 or game_share >= 0.25 → pixel_perfect
    assert "pixel_perfect" in badges
    assert "data_wrangler" in badges


def test_badges_skill_driven_test_and_data_and_container():
    # No category data; only skills should drive these badges
    snap = make_snapshot(
        languages={"Python": 100.0},
        skills={"Docker", "PyTest", "Pandas"},
    )

    badges = assign_badges(snap)

    # Docker → container_captain
    assert "container_captain" in badges
    # PyTest → test_pilot (skill-based)
    assert "test_pilot" in badges
    # Pandas → data_wrangler (skill-based)
    assert "data_wrangler" in badges


def test_badge_full_stack_explorer():
    # Backend + frontend + React stack → full_stack_explorer
    snap = make_snapshot(
        languages={"Python": 60.0, "JavaScript": 40.0},
        skills={"React"},
    )

    badges = assign_badges(snap)

    assert "full_stack_explorer" in badges


# ---------------------------------------------------------------------------
# build_fun_facts
# ---------------------------------------------------------------------------


def test_fun_facts_correspond_to_badges_and_basic_stats():
    snap = make_snapshot(
        name="MyProject",
        total_files=100,
        total_size_mb=1500.0,
        duration_days=42,
        languages={"Python": 50.0, "JavaScript": 50.0},
        skills={"Docker", "PyTest"},
        author_count=1,
        collaboration_status="individual",
        category_summary={
            "test": {"file_share": 0.2},
            "docs": {"file_share": 0.3},
        },
    )
    badges = assign_badges(snap)
    facts = build_fun_facts(snap, badges)

    # Should always get the generic "evolving for X days" fact if duration > 0
    assert any("42 day(s)" in f for f in facts)

    if "gigantana" in badges:
        assert any("weighs in at" in f for f in facts)

    if "solo_runner" in badges:
        assert any("solo contributor" in f for f in facts)

    if "team_effort" in badges:
        assert any("collaborator(s)" in f for f in facts)

    if "test_pilot" in badges:
        assert any("Test code represents" in f for f in facts)

    if "docs_guardian" in badges:
        assert any("documentation footprint" in f for f in facts)

    if "container_captain" in badges:
        assert any("Containerization is part" in f for f in facts)


# ---------------------------------------------------------------------------
# aggregate_badges
# ---------------------------------------------------------------------------


@dataclass
class DummyProject:
    badges: Iterable[str]


def test_aggregate_badges_counts_correctly():
    projects = [
        DummyProject(badges=["a", "b", "a"]),
        DummyProject(badges=["b", "c"]),
        DummyProject(badges=[]),
        DummyProject(badges=["a"]),
    ]

    totals = aggregate_badges(projects)

    assert totals == {"a": 3, "b": 2, "c": 1}


def test_aggregate_badges_handles_missing_badges_attr():
    class NoBadges:
        pass

    projects = [
        NoBadges(),
        DummyProject(badges=["x", "y"]),
    ]

    totals = aggregate_badges(projects)

    assert totals == {"x": 1, "y": 1}
