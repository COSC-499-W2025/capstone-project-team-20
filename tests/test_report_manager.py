import pytest
import sqlite3
import os
from datetime import datetime, timedelta

from src.managers.ReportManager import ReportManager
from src.models.Report import Report
from src.models.ReportProject import ReportProject, PortfolioDetails

DB_PATH = "test_reports.db"

@pytest.fixture
def manager():
    """Create a ReportManager with a test database, and clean up after."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    yield ReportManager(db_path=DB_PATH)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def make_project(name, score):
    return ReportProject(
        project_name=name,
        resume_score=score,
        bullets=["bullet"],
        summary="summary",
        portfolio_details=PortfolioDetails(project_name=name)
    )

def test_create_and_get_full_report(manager: ReportManager):
    """Tests creating a report and retrieving it with all its child projects."""
    p1 = make_project("Project A", 90)
    p2 = make_project("Project B", 80)
    original_report = Report(title="My Test Report", projects=[p1, p2])

    # Create the report
    saved_report = manager.create_report(original_report)
    assert saved_report is not None
    assert saved_report.id is not None
    report_id = saved_report.id

    # Retrieve and verify
    retrieved_report = manager.get_report(report_id)
    assert retrieved_report is not None
    assert retrieved_report.id == report_id
    assert retrieved_report.title == "My Test Report"
    assert len(retrieved_report.projects) == 2

    # Verify project details
    project_names = {p.project_name for p in retrieved_report.projects}
    assert project_names == {"Project A", "Project B"}
    assert retrieved_report.projects[0].resume_score == 90
    assert retrieved_report.projects[0].portfolio_details.project_name == "Project A"
