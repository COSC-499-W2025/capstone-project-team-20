import pytest
import sqlite3
import os
from datetime import datetime

from src.managers.ReportManager import ReportManager
from src.models.Report import Report
from src.models.ReportProject import ReportProject, PortfolioDetails

DB_PATH = "test_reports.db"

@pytest.fixture
def manager():
    """Provides a ReportManager with a clean database for each test."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    yield ReportManager(db_path=DB_PATH)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

def make_project(name="Proj", score=80):
    return ReportProject(
        project_name=name,
        resume_score=score,
        bullets=["bullet one"],
        summary="This is a summary.",
        portfolio_details=PortfolioDetails(project_name=name, overview="Overview."),
        date_created=datetime.now(),
        last_modified=datetime.now()
    )

def test_create_and_get_full_report(manager: ReportManager):
    """Tests creating a report with projects and retrieving it."""
    report = Report(title="My Test Report", projects=[make_project("P1"), make_project("P2")])

    saved_report = manager.create_report(report)
    assert saved_report is not None
    assert saved_report.id is not None

    retrieved_report = manager.get_report(saved_report.id)

    assert retrieved_report is not None
    assert retrieved_report.id == saved_report.id
    assert retrieved_report.title == "My Test Report"
    assert len(retrieved_report.projects) == 2
    assert retrieved_report.projects[0].project_name == "P1"
    assert retrieved_report.projects[1].summary == "This is a summary."
    assert isinstance(retrieved_report.projects[0].portfolio_details, PortfolioDetails)
    assert retrieved_report.projects[0].portfolio_details.overview == "Overview."
