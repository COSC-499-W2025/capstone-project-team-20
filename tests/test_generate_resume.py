from datetime import datetime
from unittest.mock import MagicMock
from pathlib import Path
import pytest
import zipfile

from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager
from src.managers.ProjectManager import ProjectManager
from src.managers.FileHashManager import FileHashManager
from src.models.Project import Project
from src.ZipParser import parse_zip_to_project_folders
from src.ProjectFolder import ProjectFolder


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_config_manager():
    return MagicMock(spec=ConfigManager)


@pytest.fixture
def analyzer_base(mock_config_manager):
    """Analyzer for non-resume tests."""
    dummy_zip = Path("/dummy/path.zip")
    return ProjectAnalyzer(
        config_manager=mock_config_manager,
        root_folders=[],
        zip_path=dummy_zip
    )


@pytest.fixture
def analyzer_resume(mock_config_manager):
    """Analyzer for resume generation tests."""
    dummy_zip = Path("/dummy/path.zip")
    a = ProjectAnalyzer(
        config_manager=mock_config_manager,
        root_folders=[],
        zip_path=dummy_zip
    )
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

    class R:
        def __init__(self):
            self.id = 1
            self.title = "My Report"
            self.date_created = datetime.now()
            self.projects = [P()]
            self.average_score = 4.5
            self.notes = "Some notes"

    return R()

# ============================================================
# _generate_resume tests
# ============================================================

def test_generate_resume_success(tmp_path, sample_report, mock_config_manager):
    analyzer = ProjectAnalyzer(mock_config_manager, [], Path("/dummy.zip"))
    analyzer._config_manager.get.return_value = "value"

    with pytest.MonkeyPatch().context() as mp:
        mock_exporter = MagicMock()
        mp.setattr("src.analyzers.ProjectAnalyzer.ReportExporter", lambda: mock_exporter)

        out = analyzer._generate_resume(sample_report, "resume.pdf")

    assert out.name == "resume.pdf"
    mock_exporter.export_to_pdf.assert_called_once()


def test_generate_resume_missing_projects(mock_config_manager):
    analyzer = ProjectAnalyzer(mock_config_manager, [], Path("/dummy.zip"))
    analyzer._config_manager.get.return_value = "value"

    class R:
        projects = []

    with pytest.raises(ValueError):
        analyzer._generate_resume(R(), "resume.pdf")


def test_generate_resume_missing_config_fields(sample_report, mock_config_manager):
    analyzer = ProjectAnalyzer(mock_config_manager, [], Path("/dummy.zip"))
    analyzer._config_manager.get.side_effect = lambda k: None if k == "email" else "x"

    with pytest.raises(ValueError):
        analyzer._generate_resume(sample_report, "resume.pdf")


def test_generate_resume_runtime_error_from_exporter(sample_report, mock_config_manager):
    analyzer = ProjectAnalyzer(mock_config_manager, [], Path("/dummy.zip"))
    analyzer._config_manager.get.return_value = "x"

    with pytest.MonkeyPatch().context() as mp:
        mock_exporter = MagicMock()
        mock_exporter.export_to_pdf.side_effect = RuntimeError("latex missing")
        mp.setattr("src.analyzers.ProjectAnalyzer.ReportExporter", lambda: mock_exporter)

        with pytest.raises(RuntimeError):
            analyzer._generate_resume(sample_report, "resume.pdf")


# ============================================================
# trigger_resume_generation tests
# ============================================================

def test_trigger_resume_generation_no_reports(analyzer_resume, monkeypatch):
    analyzer_resume.report_manager.list_reports_summary.return_value = []
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() is None


def test_trigger_resume_generation_cancel_on_id(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "Test", "date_created": "2024-01-01T12:00:00", "project_count": 1}
    ]

    # FIX: get_report must return a real report so formatting doesn't explode
    analyzer_resume.report_manager.get_report.return_value = sample_report

    monkeypatch.setattr("builtins.input", lambda _: "q")
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() is None



def test_trigger_resume_generation_invalid_id_then_valid(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "Test", "date_created": "2024-01-01T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = sample_report

    inputs = iter(["999", "1", "", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(analyzer_resume, "_generate_resume", lambda *a, **k: Path("resume.pdf"))
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() == Path("resume.pdf")


def test_trigger_resume_generation_load_report_error(analyzer_resume, monkeypatch):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "Test", "date_created": "2024-01-01T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = None

    monkeypatch.setattr("builtins.input", lambda _: "1")
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() is None


def test_trigger_resume_generation_filename_custom(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "Test", "date_created": "2024-01-01T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = sample_report

    inputs = iter(["1", "custom_name", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(analyzer_resume, "_generate_resume", lambda *a, **k: Path("custom_name.pdf"))
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() == Path("custom_name.pdf")


def test_trigger_resume_generation_filename_default(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "My Report", "date_created": "2024-01-01T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = sample_report

    inputs = iter(["1", "", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(analyzer_resume, "_generate_resume", lambda *a, **k: Path("my_report_resume.pdf"))
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() == Path("my_report_resume.pdf")


def test_trigger_resume_generation_cancel_on_confirm(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "Test", "date_created": "2024-01-01T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = sample_report

    inputs = iter(["1", "", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() is None


def test_trigger_resume_generation_generate_raises_value_error(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "Test", "date_created": "2024-01-01T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = sample_report

    inputs = iter(["1", "", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(analyzer_resume, "_generate_resume",
                        lambda *a, **k: (_ for _ in ()).throw(ValueError("bad config")))
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() is None


def test_trigger_resume_generation_generate_raises_runtime_error(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "Test", "date_created": "2024-01-01T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = sample_report

    inputs = iter(["1", "", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(analyzer_resume, "_generate_resume",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("latex missing")))
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() is None
