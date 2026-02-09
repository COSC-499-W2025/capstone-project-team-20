import io
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
from contextlib import redirect_stdout

from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.models.ReportProject import PortfolioDetails

class DummyProject:
    def __init__(self, name, portfolio_details, last_modified=None):
        self.name = name
        self.portfolio_details = portfolio_details
        self.last_modified = last_modified

def test_retrieve_full_portfolio_aggregates_and_sorts(monkeypatch):
    analyzer = ProjectAnalyzer(MagicMock(), [], Path("."))
    projects = [
        DummyProject("A", PortfolioDetails(project_name="A", overview="Overview A"), datetime(2025, 2, 1)),
        DummyProject("B", PortfolioDetails(project_name="B", overview="Overview B"), datetime(2025, 3, 1)),
        DummyProject("C", PortfolioDetails(), datetime(2025, 1, 1)),  # Empty details should be skipped
    ]

    monkeypatch.setattr("builtins.input", lambda _: "n")

    with patch.object(ProjectAnalyzer, "_get_projects", return_value=projects):
        buf = io.StringIO()
        with redirect_stdout(buf):
            analyzer.retrieve_full_portfolio()
        out = buf.getvalue()

    assert "PROFESSIONAL PORTFOLIO" in out
    assert "Overview B" in out
    assert "Overview A" in out
    # Ensure B (newest) appears before A
    assert out.find("Overview B") < out.find("Overview A")
    # C is skipped
    assert "Overview C" not in out

def test_retrieve_full_portfolio_handles_empty(monkeypatch):
    analyzer = ProjectAnalyzer(MagicMock(), [], Path("."))
    projects = [DummyProject("X", PortfolioDetails(), None)]

    with patch.object(ProjectAnalyzer, "_get_projects", return_value=projects):
        buf = io.StringIO()
        with redirect_stdout(buf):
            analyzer.retrieve_full_portfolio()
        out = buf.getvalue()

    assert "No portfolio entries found" in out
