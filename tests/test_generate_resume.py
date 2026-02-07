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
    analyzer_resume.report_manager.get_report.return_value = None  # <- add this

    monkeypatch.setattr("builtins.input", lambda _="": "q")
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() is None




def test_trigger_resume_generation_export_base_success(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "My Report", "date_created": "2026-02-07T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = sample_report
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    # Patch exporter + manager
    mock_exporter = MagicMock()
    mock_exporter._build_context.return_value = {"name": "X", "projects": []}

    mock_variant_mgr = MagicMock()

    monkeypatch.setattr("src.analyzers.ProjectAnalyzer.ReportExporter", lambda: mock_exporter)
    monkeypatch.setattr("src.analyzers.ProjectAnalyzer.ResumeVariantManager", lambda *_: mock_variant_mgr)

    # Inputs:
    # report id 1
    # filename "" -> default
    # confirm y
    # menu 1 -> export base
    _feed(monkeypatch, ["1", "", "y", "1"])

    out = analyzer_resume.trigger_resume_generation()

    assert out == Path("resumes") / "my_report_resume.pdf"
    mock_exporter._build_context.assert_called_once()
    mock_variant_mgr.ensure_base_snapshot.assert_called_once()
    mock_exporter.export_context_to_pdf.assert_called_once()


def test_trigger_resume_generation_edit_and_export_variant(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "My Report", "date_created": "2026-02-07T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = sample_report
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    mock_exporter = MagicMock()
    base_ctx = {"name": "Base", "projects": [{"name": "P", "bullets": ["a"]}]}
    edited_ctx = {"name": "Edited", "projects": [{"name": "P", "bullets": ["b"]}]}
    mock_exporter._build_context.return_value = base_ctx

    mock_variant_mgr = MagicMock()

    mock_editor = MagicMock()
    mock_editor.edit_variant_cli.return_value = edited_ctx

    monkeypatch.setattr("src.analyzers.ProjectAnalyzer.ReportExporter", lambda: mock_exporter)
    monkeypatch.setattr("src.analyzers.ProjectAnalyzer.ResumeVariantManager", lambda *_: mock_variant_mgr)
    monkeypatch.setattr("src.analyzers.ProjectAnalyzer.ResumeVariantEditor", lambda: mock_editor)

    # Inputs:
    # pick report id 1
    # filename "resume.pdf"
    # confirm y
    # menu 2 -> edit + export
    # then editor finishes internally (we mocked it)
    _feed(monkeypatch, ["1", "resume.pdf", "y", "2"])

    out = analyzer_resume.trigger_resume_generation()

    assert out == Path("resumes") / "resume_updated.pdf"
    mock_variant_mgr.create_variant.assert_called_once()
    mock_exporter.export_context_to_pdf.assert_called_once_with(
        edited_ctx, output_path="resume_updated.pdf", template="jake"
    )


def test_trigger_resume_generation_cancel_on_confirm(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "My Report", "date_created": "2026-02-07T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = sample_report

    monkeypatch.setattr("builtins.print", lambda *a, **k: None)
    _feed(monkeypatch, ["1", "", "n"])

    assert analyzer_resume.trigger_resume_generation() is None
