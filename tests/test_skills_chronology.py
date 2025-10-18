import pytest
from datetime import date, datetime

from src.SkillsChronology import SkillsChronology, SkillEvent


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


def test_build_timeline_sorted_and_complete():
    sc = SkillsChronology()
    events = sc.build_timeline(sample_projects())

    # Ensure it's sorted by date then skill
    assert [e.when for e in events] == sorted([e.when for e in events])

    # Check a couple of concrete entries
    assert events[0] == SkillEvent(when=date(2023, 1, 10), skill="pytest", project="Proj Alpha") \
           or events[1] == SkillEvent(when=date(2023, 1, 10), skill="pytest", project="Proj Alpha")
    assert any(e.skill == "docker" and e.project == "Proj Beta" for e in events)


def test_first_use_by_skill_deduplicates_and_orders():
    sc = SkillsChronology()
    firsts = sc.first_use_by_skill(sample_projects())

    # Expect first time each skill is seen
    expected = {
        "python": date(2023, 1, 10),
        "pytest": date(2023, 1, 10),
        "sqlite": date(2023, 2, 1),
        "docker": date(2023, 3, 5),
    }
    assert dict(firsts) == expected

    # Ensure order is chronological (pytest/python share the same day, order by name)
    assert firsts == [
        ("pytest", date(2023, 1, 10)),
        ("python", date(2023, 1, 10)),
        ("sqlite", date(2023, 2, 1)),
        ("docker", date(2023, 3, 5)),
    ]


def test_handles_empty_input():
    sc = SkillsChronology()
    assert sc.build_timeline([]) == []
    assert sc.first_use_by_skill([]) == []


def test_rejects_invalid_date_format():
    sc = SkillsChronology()
    projects = [{"name": "Bad", "skills": ["x"], "date": "2023/01/10"}]  # not ISO
    with pytest.raises(ValueError):
        sc.build_timeline(projects)
