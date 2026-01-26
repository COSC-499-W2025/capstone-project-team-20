import io
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock
from contextlib import redirect_stdout

from src.analyzers.ProjectAnalyzer import ProjectAnalyzer

class DummyProject:
    def __init__(self, name, entry, last_modified=None):
        self.name = name
        self.portfolio_entry = entry
        self.last_modified = last_modified

def test_retrieve_full_portfolio_aggregates_and_sorts():
    analyzer = ProjectAnalyzer(MagicMock(), [], Path("."))
    projects = [
        DummyProject("A", "### A\n**Role:** Team Contributor (A) | **Timeline:** 1 month\n", datetime(2025, 2, 1)),
        DummyProject("B", "### B\n**Role:** Team Contributor (B) | **Timeline:** 2 months\n", datetime(2025, 3, 1)),
        DummyProject("C", "", datetime(2025, 1, 1)),  # empty entry should be skipped
    ]

    with patch.object(ProjectAnalyzer, "_get_projects", return_value=projects):
        buf = io.StringIO()
        with redirect_stdout(buf):
            analyzer.retrieve_full_portfolio()
        out = buf.getvalue()

    assert "PROFESSIONAL PORTFOLIO" in out

    # matching characters in the main header.
    entry_b_identifier = "Team Contributor (B)"
    entry_a_identifier = "Team Contributor (A)"

    assert entry_b_identifier in out
    assert entry_a_identifier in out

    # Ensure the entry for B (the newer project) appears before the entry for A.
    assert out.find(entry_b_identifier) < out.find(entry_a_identifier)

    # C is skipped
    assert "### C" not in out
    assert "Total Projects in Portfolio: 2" in out

def test_retrieve_full_portfolio_handles_empty():
    analyzer = ProjectAnalyzer(MagicMock(), [], Path("."))
    projects = [DummyProject("X", "", None)]

    with patch.object(ProjectAnalyzer, "_get_projects", return_value=projects):
        buf = io.StringIO()
        with redirect_stdout(buf):
            analyzer.retrieve_full_portfolio()
        out = buf.getvalue()

    assert "No portfolio entries found" in out
