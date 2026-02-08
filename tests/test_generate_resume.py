from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager


@pytest.fixture
def mock_config_manager():
    return MagicMock(spec=ConfigManager)


@pytest.fixture
def analyzer_resume(mock_config_manager):
    a = ProjectAnalyzer(mock_config_manager, [], Path("/dummy/path.zip"))
    a.report_manager = MagicMock()
    return a


@pytest.fixture
def sample_report():
    class P:
        def __init__(self):
            self.project_name = "Proj"
            self.languages = ["Python"]
            self.frameworks = ["FastAPI"]
            self.resume_score = 4.5
            self.bullets = ["a"]
            self.date_created = datetime(2026, 1, 1)
            self.last_modified = datetime(2026, 2, 1)

    class R:
        def __init__(self):
            self.id = 1
            self.title = "My Report"
            self.date_created = datetime(2026, 2, 7, 12, 0)
            self.projects = [P()]
            self.average_score = 4.5
            self.notes = "Some notes"
            # optional: if your code uses sort_by
            self.sort_by = "resume_score"

    return R()


def _feed(monkeypatch, values):
    it = iter(values)
    monkeypatch.setattr("builtins.input", lambda _="": next(it))


def test_trigger_resume_generation_no_reports(analyzer_resume, monkeypatch):
    analyzer_resume.report_manager.list_reports_summary.return_value = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() is None


def test_trigger_resume_generation_cancel_on_id(analyzer_resume, monkeypatch):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "Test", "date_created": "2026-02-07T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = None

    monkeypatch.setattr("builtins.input", lambda _="": "q")
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() is None


def test_trigger_resume_generation_export_base_success(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "My Report", "date_created": "2026-02-07T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = sample_report
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    mock_exporter = MagicMock()
    analyzer_resume.report_exporter = mock_exporter


    # Inputs:
    # report id 1
    # filename "" -> default
    # confirm y
    # menu 1 -> export base
    _feed(monkeypatch, ["1", "", "y", "1"])

    out = analyzer_resume.trigger_resume_generation()

    assert out == Path("resumes") / "my_report_resume.pdf"
    mock_exporter.export_to_pdf.assert_called_once()
    # Optional stronger assertion (if your function calls like this):
    # mock_exporter.export_to_pdf.assert_called_once_with(
    #     sample_report, analyzer_resume._config_manager, output_path="my_report_resume.pdf", template="jake"
    # )


def test_trigger_resume_generation_edit_and_export_report(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "My Report", "date_created": "2026-02-07T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = sample_report
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    # ✅ patch the already-created exporter instance
    mock_exporter = MagicMock()
    analyzer_resume.report_exporter = mock_exporter

    # ✅ patch the editor constructor used INSIDE ProjectAnalyzer.py
    mock_editor = MagicMock()
    mock_editor.edit_report_cli.return_value = True  # your code checks `if not edited: ...`
    monkeypatch.setattr("src.analyzers.ProjectAnalyzer.ReportEditor", lambda *a, **k: mock_editor)

    analyzer_resume.report_manager.update_report.return_value = True

    # Inputs:
    _feed(monkeypatch, ["1", "resume.pdf", "y", "2"])

    out = analyzer_resume.trigger_resume_generation()

    assert out == Path("resumes") / "resume_updated.pdf"

    mock_editor.edit_report_cli.assert_called_once()
    analyzer_resume.report_manager.update_report.assert_called_once_with(sample_report)
    mock_exporter.export_to_pdf.assert_called_once()



def test_trigger_resume_generation_cancel_on_confirm(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "My Report", "date_created": "2026-02-07T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = sample_report

    monkeypatch.setattr("builtins.print", lambda *a, **k: None)
    _feed(monkeypatch, ["1", "", "n"])

    assert analyzer_resume.trigger_resume_generation() is None
