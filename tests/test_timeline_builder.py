import pytest
from datetime import date, datetime, timedelta

from utils.timeline_builder import (
    build_timeline,
    first_use_by_skill,
    projects_chronologically,
    projects_with_skills_chronologically,
    SkillEvent,
)


def sample_projects():
    return [
        {
            "name": "Proj Alpha",
            "skills": ["python", "pytest"],
            "date": "2023-01-10",
        },
        {
            "name": "Proj Beta",
            "skills": ["docker", "python"],
            "date": date(2023, 3, 5),
        },
        {
            "name": "Proj Gamma",
            "skills": ["sqlite", "pytest"],
            "start_date": datetime(2023, 2, 1),
        },
    ]


# ---------- Core behavior for build_timeline / first_use_by_skill ----------

def test_build_timeline_sorted_and_complete():
    events = build_timeline(sample_projects())

    # Sorted by date (then by skill, then by project)
    assert [e.when for e in events] == sorted([e.when for e in events])

    # Contains representative events
    assert any(e == SkillEvent(when=date(2023, 1, 10), skill="pytest", project="Proj Alpha") for e in events)
    assert any(e.skill == "docker" and e.project == "Proj Beta" for e in events)


def test_first_use_by_skill_deduplicates_and_orders():
    firsts = first_use_by_skill(sample_projects())

    expected = {
        "python": date(2023, 1, 10),
        "pytest": date(2023, 1, 10),
        "sqlite": date(2023, 2, 1),
        "docker": date(2023, 3, 5),
    }
    assert dict(firsts) == expected

    # Ordered by first_seen_date then skill name (case-insensitive)
    assert firsts == [
        ("pytest", date(2023, 1, 10)),
        ("python", date(2023, 1, 10)),
        ("sqlite", date(2023, 2, 1)),
        ("docker", date(2023, 3, 5)),
    ]


def test_handles_empty_input():
    assert build_timeline([]) == []
    assert first_use_by_skill([]) == []
    assert projects_chronologically([]) == []
    assert projects_with_skills_chronologically([]) == []


def test_rejects_invalid_date_format():
    projects = [{"name": "Bad", "skills": ["x"], "date": "2023/01/10"}]
    with pytest.raises(ValueError):
        build_timeline(projects)
    with pytest.raises(ValueError):
        projects_chronologically(projects)
    with pytest.raises(ValueError):
        projects_with_skills_chronologically(projects)


def test_missing_all_date_fields_errors():
    projects = [{"name": "NoDate", "skills": ["x"]}]
    with pytest.raises(ValueError):
        build_timeline(projects)


# ---------- Additional coverage & edge cases ----------

def test_accepts_all_supported_date_types_and_normalizes():
    today = date(2024, 4, 2)
    tomorrow_dt = datetime(2024, 4, 3, 12, 0)
    iso = "2024-04-04"

    projects = [
        {"name": "D1", "skills": ["a"], "date": today},
        {"name": "D2", "skills": ["b"], "date": tomorrow_dt},   # datetime -> .date()
        {"name": "D3", "skills": ["c"], "date": iso},           # ISO string
    ]
    events = build_timeline(projects)

    # Ensure dates normalized and in ascending order
    assert [e.when for e in events] == [today, tomorrow_dt.date(), date(2024, 4, 4)]


def test_date_priority_date_over_start_over_end():
    base = date(2023, 6, 1)
    earlier = base - timedelta(days=10)
    later = base + timedelta(days=10)

    # Case 1: all present -> `date` wins
    p1 = [{
        "name": "P",
        "skills": ["x"],
        "date": base,
        "start_date": earlier,
        "end_date": later,
    }]
    ev1 = build_timeline(p1)[0]
    assert ev1.when == base

    # Case 2: only start_date present
    p2 = [{"name": "P2", "skills": ["x"], "start_date": earlier}]
    ev2 = build_timeline(p2)[0]
    assert ev2.when == earlier

    # Case 3: only end_date present
    p3 = [{"name": "P3", "skills": ["x"], "end_date": later}]
    ev3 = build_timeline(p3)[0]
    assert ev3.when == later


def test_ignores_empty_or_nonstring_skills():
    projects = [{
        "name": "P",
        "skills": ["python", "", "   ", None, 123, "PyTest"],
        "date": "2023-01-01",
    }]
    events = build_timeline(projects)
    skills = sorted({e.skill.lower() for e in events})
    assert skills == ["pytest", "python"]  # only valid non-empty strings


def test_sorting_tiebreakers_when_same_date():
    # Two projects on same day with overlapping skills
    projects = [
        {"name": "B Project", "skills": ["b", "a"], "date": "2024-05-01"},
        {"name": "A Project", "skills": ["a"], "date": "2024-05-01"},
    ]
    events = build_timeline(projects)

    # Events are ordered by (when, skill, project); so for 2024-05-01:
    # skill 'a' comes before 'b', and among 'a' ties, "A Project" < "B Project".
    expected = [
        SkillEvent(date(2024, 5, 1), "a", "A Project"),
        SkillEvent(date(2024, 5, 1), "a", "B Project"),
        SkillEvent(date(2024, 5, 1), "b", "B Project"),
    ]
    assert events == expected


# ---------- Project helper functions ----------

def test_projects_chronologically_simple():
    ordered = projects_chronologically(sample_projects())
    assert ordered == [
        (date(2023, 1, 10), "Proj Alpha"),
        (date(2023, 2, 1), "Proj Gamma"),
        (date(2023, 3, 5), "Proj Beta"),
    ]


def test_projects_with_skills_chronologically_groups_and_sorts_skills():
    rows = projects_with_skills_chronologically(sample_projects())

    # dates in ascending order
    assert [r[0] for r in rows] == sorted([r[0] for r in rows])

    # First row: Proj Alpha skills are unique and case-insensitively sorted
    first = rows[0]
    assert first[0] == date(2023, 1, 10)
    assert first[1] == "Proj Alpha"
    assert first[2] == ["python", "pytest"]


def test_projects_helpers_dedupe_by_name_keep_first_occurrence():
    # Duplicate name with different dates — first occurrence should be kept
    projects = [
        {"name": "Same", "skills": ["a"], "date": "2024-01-01"},
        {"name": "Same", "skills": ["b"], "date": "2024-02-01"},
        {"name": "Other", "skills": ["c"], "date": "2024-01-15"},
    ]

    ordered = projects_chronologically(projects)
    assert ordered == [
        (date(2024, 1, 1), "Same"),
        (date(2024, 1, 15), "Other"),
    ]

    grouped = projects_with_skills_chronologically(projects)
    assert grouped[0][1:] == ("Same", ["a"])   # first "Same" wins, skill list from first only
    assert grouped[1][1:] == ("Other", ["c"])


def test_projects_with_skills_case_insensitive_sorting():
    projects = [
        {"name": "N", "skills": ["PyTest", "python", "PYTHON", "pytest", "Zed", "alpha"], "date": "2024-03-03"},
    ]
    rows = projects_with_skills_chronologically(projects)
    # Unique + case-insensitive sort => alpha, PyTest/pytest together, python once, Zed last
    assert rows[0][2] == ["alpha", "PyTest", "python", "Zed"]
