"""
Tests for delete_report functionality:
  - ProjectAnalyzer.delete_report (CLI flow)
  - ReportManager.delete_report (persistence layer)
"""

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def make_report(id=1, title="Test Report", num_projects=2):
    """Return a minimal mock Report object."""
    report = MagicMock()
    report.id = id
    report.title = title
    report.projects = [MagicMock() for _ in range(num_projects)]
    return report


def make_summary(id=1, title="Test Report", project_count=2):
    """Return a minimal report-summary dict (as returned by list_reports_summary)."""
    return {
        "id": id,
        "title": title,
        "date_created": "2025-01-15T10:30:00",
        "project_count": project_count,
    }


def make_analyzer(reports_summary=None, report=None):
    """
    Build a ProjectAnalyzer-like object with report_manager stubbed out.
    Avoids instantiating the real class (which needs ZIPs, DB, etc.).
    """
    analyzer = MagicMock()
    analyzer.report_manager = MagicMock()
    analyzer.report_manager.list_reports_summary.return_value = (
        reports_summary if reports_summary is not None else [make_summary()]
    )
    analyzer.report_manager.get_report.return_value = (
        report if report is not None else make_report()
    )
    analyzer.report_manager.delete_report.return_value = True
    # Bind the real method to our mock instance
    from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
    analyzer.delete_report = ProjectAnalyzer.delete_report.__get__(analyzer, type(analyzer))
    return analyzer


# ---------------------------------------------------------------------------
# ReportManager.delete_report
# ---------------------------------------------------------------------------

class TestReportManagerDeleteReport:

    def test_delete_existing_report_returns_true(self):
        """delete_report delegates to StorageManager.delete and returns its result."""
        manager = MagicMock()
        manager.delete.return_value = True

        from src.managers.ReportManager import ReportManager
        result = ReportManager.delete_report(manager, id=1)

        manager.delete.assert_called_once_with(1)
        assert result is True

    def test_delete_nonexistent_report_returns_false(self):
        """Returns False when underlying delete finds no row."""
        manager = MagicMock()
        manager.delete.return_value = False

        from src.managers.ReportManager import ReportManager
        result = ReportManager.delete_report(manager, id=999)

        assert result is False

    def test_delete_passes_correct_id(self):
        """Ensures the correct id is forwarded to StorageManager.delete."""
        manager = MagicMock()
        manager.delete.return_value = True

        from src.managers.ReportManager import ReportManager
        ReportManager.delete_report(manager, id=42)

        manager.delete.assert_called_once_with(42)


# ---------------------------------------------------------------------------
# ProjectAnalyzer.delete_report — no reports exist
# ---------------------------------------------------------------------------

class TestDeleteReportNoReports:

    def test_prints_no_reports_message_and_returns(self, capsys):
        analyzer = make_analyzer(reports_summary=[])

        analyzer.delete_report()

        captured = capsys.readouterr()
        assert "don't have any stored reports" in captured.out
        analyzer.report_manager.delete_report.assert_not_called()

    def test_does_not_call_get_report_when_no_summaries(self):
        analyzer = make_analyzer(reports_summary=[])

        analyzer.delete_report()

        analyzer.report_manager.get_report.assert_not_called()


# ---------------------------------------------------------------------------
# ProjectAnalyzer.delete_report — user cancels
# ---------------------------------------------------------------------------

class TestDeleteReportUserCancels:

    @patch("builtins.input", return_value="q")
    def test_cancel_at_id_prompt_does_not_delete(self, mock_input):
        analyzer = make_analyzer()

        analyzer.delete_report()

        analyzer.report_manager.delete_report.assert_not_called()

    @patch("builtins.input", side_effect=["1", "n"])
    def test_cancel_at_confirmation_does_not_delete(self, mock_input):
        analyzer = make_analyzer()

        analyzer.delete_report()

        analyzer.report_manager.delete_report.assert_not_called()

    @patch("builtins.input", side_effect=["1", "N"])
    def test_cancel_confirmation_is_case_insensitive(self, mock_input):
        analyzer = make_analyzer()

        analyzer.delete_report()

        analyzer.report_manager.delete_report.assert_not_called()


# ---------------------------------------------------------------------------
# ProjectAnalyzer.delete_report — happy path
# ---------------------------------------------------------------------------

class TestDeleteReportSuccess:

    @patch("builtins.input", side_effect=["1", "y"])
    def test_successful_delete_calls_manager(self, mock_input):
        analyzer = make_analyzer()

        analyzer.delete_report()

        analyzer.report_manager.delete_report.assert_called_once_with(1)

    @patch("builtins.input", side_effect=["1", "y"])
    def test_successful_delete_prints_confirmation(self, mock_input, capsys):
        analyzer = make_analyzer(report=make_report(title="My Report"))

        analyzer.delete_report()

        captured = capsys.readouterr()
        assert "My Report" in captured.out
        assert "deleted" in captured.out.lower()

    @patch("builtins.input", side_effect=["2", "y"])
    def test_deletes_correct_report_when_multiple_exist(self, mock_input):
        summaries = [make_summary(id=1, title="First"), make_summary(id=2, title="Second")]
        report2 = make_report(id=2, title="Second")
        analyzer = make_analyzer(reports_summary=summaries, report=report2)
        analyzer.report_manager.get_report.return_value = report2

        analyzer.delete_report()

        analyzer.report_manager.delete_report.assert_called_once_with(2)


# ---------------------------------------------------------------------------
# ProjectAnalyzer.delete_report — invalid input, loop continues
# ---------------------------------------------------------------------------

class TestDeleteReportInvalidInput:

    @patch("builtins.input", side_effect=["999", "1", "y"])
    def test_invalid_id_then_valid_id_succeeds(self, mock_input):
        """After an invalid ID the loop should let the user try again."""
        analyzer = make_analyzer(reports_summary=[make_summary(id=1)])

        analyzer.delete_report()

        analyzer.report_manager.delete_report.assert_called_once_with(1)

    @patch("builtins.input", side_effect=["abc", "1", "y"])
    def test_non_numeric_then_valid_succeeds(self, mock_input):
        analyzer = make_analyzer()

        analyzer.delete_report()

        analyzer.report_manager.delete_report.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# ProjectAnalyzer.delete_report — get_report failure loops, not exits
# ---------------------------------------------------------------------------

class TestDeleteReportGetReportFailure:

    @patch("builtins.input", side_effect=["1", "q"])
    def test_get_report_none_prints_error(self, mock_input, capsys):
        analyzer = make_analyzer()
        analyzer.report_manager.get_report.return_value = None

        analyzer.delete_report()

        captured = capsys.readouterr()
        assert "Error" in captured.out or "error" in captured.out


# ---------------------------------------------------------------------------
# ProjectAnalyzer.delete_report — delete_report returns False
# ---------------------------------------------------------------------------

class TestDeleteReportManagerFailure:

    @patch("builtins.input", side_effect=["1", "y"])
    def test_failed_delete_prints_failure_message(self, mock_input, capsys):
        analyzer = make_analyzer()
        analyzer.report_manager.delete_report.return_value = False

        analyzer.delete_report()

        captured = capsys.readouterr()
        assert "Failed" in captured.out or "failed" in captured.out

    @patch("builtins.input", side_effect=["1", "y"])
    def test_failed_delete_does_not_raise(self, mock_input):
        analyzer = make_analyzer()
        analyzer.report_manager.delete_report.return_value = False

        analyzer.delete_report()  # should not raise