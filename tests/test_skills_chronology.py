import pytest
from datetime import date, datetime

from utils.skills_chronology import (
    build_timeline,
    first_use_by_skill,
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


def test_build_timeline_sorted_and_complete():
    events = build_timeline(sample_projects())

    assert [e.when for e in events] == sorted([e.when for e in events])

    assert events[0] == SkillEvent(when=date(2023, 1, 10), skill="pytest", project="Proj Alpha") \
           or events[1] == SkillEvent(when=date(2023, 1, 10), skill="pytest", project="Proj Alpha")
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

    assert firsts == [
        ("pytest", date(2023, 1, 10)),
        ("python", date(2023, 1, 10)),
        ("sqlite", date(2023, 2, 1)),
        ("docker", date(2023, 3, 5)),
    ]


def test_handles_empty_input():
    assert build_timeline([]) == []
    assert first_use_by_skill([]) == []


def test_rejects_invalid_date_format():
    projects = [{"name": "Bad", "skills": ["x"], "date": "2023/01/10"}]
    with pytest.raises(ValueError):
        build_timeline(projects)
