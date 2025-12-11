import pytest
from datetime import datetime, timedelta
from src.models.Report import Report
from src.models.ReportProject import ReportProject


def test_sort_by_resume_score():
    p1 = ReportProject("A", resume_score=1)
    p2 = ReportProject("B", resume_score=5)
    p3 = ReportProject("C", resume_score=3)

    r = Report(projects=[p1, p2, p3], sort_by="resume_score")

    assert [p.project_name for p in r.projects] == ["B", "C", "A"]


def test_sort_by_date_created():
    now = datetime.now()
    p1 = ReportProject("A", date_created=now - timedelta(days=2))
    p2 = ReportProject("B", date_created=now)
    p3 = ReportProject("C", date_created=now - timedelta(days=1))

    r = Report(projects=[p1, p2, p3], sort_by="date_created")

    assert [p.project_name for p in r.projects] == ["B", "C", "A"]


def test_sort_by_last_modified():
    now = datetime.now()
    p1 = ReportProject("A", last_modified=now - timedelta(days=2))
    p2 = ReportProject("B", last_modified=now)
    p3 = ReportProject("C", last_modified=now - timedelta(days=1))

    r = Report(projects=[p1, p2, p3], sort_by="last_modified")

    assert [p.project_name for p in r.projects] == ["B", "C", "A"]


def test_add_project_resorts():
    p1 = ReportProject("A", resume_score=1)
    p2 = ReportProject("B", resume_score=5)

    r = Report(projects=[p1], sort_by="resume_score")
    r.add_project(p2)

    assert r.projects[0].project_name == "B"


def test_remove_project():
    p1 = ReportProject("A")
    p2 = ReportProject("B")

    r = Report(projects=[p1, p2])
    removed = r.remove_project("A")

    assert removed is True
    assert len(r.projects) == 1
    assert r.projects[0].project_name == "B"


def test_average_score():
    p1 = ReportProject("A", resume_score=2)
    p2 = ReportProject("B", resume_score=4)

    r = Report(projects=[p1, p2])

    assert r.average_score == 3.0


def test_all_languages():
    p1 = ReportProject("A", languages=["Python", "Go"])
    p2 = ReportProject("B", languages=["Go", "Rust"])

    r = Report(projects=[p1, p2])

    assert r.all_languages == ["Go", "Python", "Rust"]


def test_all_frameworks():
    p1 = ReportProject("A", frameworks=["Django"])
    p2 = ReportProject("B", frameworks=["FastAPI", "Django"])

    r = Report(projects=[p1, p2])

    assert r.all_frameworks == ["Django", "FastAPI"]


def test_to_dict_excludes_projects():
    r = Report(
        report_id=10,
        title="My Report",
        notes="test notes",
    )

    d = r.to_dict()

    assert d["report_id"] == 10
    assert d["title"] == "My Report"
    assert d["sort_by"] == "resume_score"
    assert d["notes"] == "test notes"
    assert "projects" not in d  # intentionally omitted

