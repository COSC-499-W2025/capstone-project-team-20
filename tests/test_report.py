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

def test_to_dict_excludes_projects():
    r = Report(id=10, title="My Report", notes="test notes", projects=[ReportProject("A")])
    d = r.to_dict()
    assert d["id"] == 10
    assert d["title"] == "My Report"
    assert "projects" not in d  # Verify 'projects' field is correctly omitted
