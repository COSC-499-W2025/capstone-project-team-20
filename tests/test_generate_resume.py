from datetime import datetime
from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest

from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager
from src.models.ReportProject import ReportProject
from src.models.Report import Report


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_config_manager():
    return MagicMock(spec=ConfigManager)


@pytest.fixture
def analyzer_base(mock_config_manager):
    dummy_zip = Path("/dummy/path.zip")
    return ProjectAnalyzer(
        config_manager=mock_config_manager,
        root_folders=[],
        zip_path=dummy_zip
    )


@pytest.fixture
def analyzer_resume(mock_config_manager):
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
            self.bullets = ["a"]

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
    analyzer_resume.report_manager.get_report.return_value = sample_report

    monkeypatch.setattr("builtins.input", lambda _: "q")
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() is None


def test_trigger_resume_generation_invalid_then_valid(analyzer_resume, monkeypatch, sample_report):
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
    monkeypatch.setattr(
        analyzer_resume,
        "_generate_resume",
        lambda *a, **k: (_ for _ in ()).throw(ValueError("bad config"))
    )
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() is None


def test_trigger_resume_generation_generate_raises_runtime_error(analyzer_resume, monkeypatch, sample_report):
    analyzer_resume.report_manager.list_reports_summary.return_value = [
        {"id": 1, "title": "Test", "date_created": "2024-01-01T12:00:00", "project_count": 1}
    ]
    analyzer_resume.report_manager.get_report.return_value = sample_report

    inputs = iter(["1", "", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr(
        analyzer_resume,
        "_generate_resume",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("latex missing"))
    )
    monkeypatch.setattr("builtins.print", lambda *a, **k: None)

    assert analyzer_resume.trigger_resume_generation() is None

def test_create_report_success():
    analyzer = MagicMock()
    analyzer.get_projects_sorted_by_score.return_value = [
        MagicMock(name="proj1", resume_score=80),
        MagicMock(name="proj2", resume_score=70),
    ]

    analyzer._select_multiple_projects.return_value = [
        MagicMock(
            name="proj1",
            resume_score=80,
            bullets=["a"],
            languages=["Python"],
            frameworks=[],
            date_created=datetime(2024, 1, 1),
            last_modified=datetime(2024, 1, 2),
        )
    ]

    analyzer.report_manager = MagicMock()

    with patch("builtins.input", side_effect=["My Report", "1"]):
        ProjectAnalyzer.create_report(analyzer)

    assert analyzer.report_manager.create_report.called
    created_report = analyzer.report_manager.create_report.call_args[0][0]
    assert created_report.title == "My Report"
    assert created_report.sort_by == "resume_score"
    assert len(created_report.projects) == 1
    assert isinstance(created_report.projects[0], ReportProject)


def test_create_report_cancel_selection():
    analyzer = MagicMock()
    analyzer.get_projects_sorted_by_score.return_value = [MagicMock()]
    analyzer._select_multiple_projects.return_value = None

    with patch("builtins.input", return_value=""):
        ProjectAnalyzer.create_report(analyzer)

    analyzer.report_manager.create_report.assert_not_called()


@pytest.fixture
def analyzer_base():
    return ProjectAnalyzer(
        config_manager=MagicMock(),
        root_folders=[],
        zip_path=Path("/dummy.zip")
    )


def test_select_multiple_projects_success(analyzer_base):
    projects = [
        MagicMock(name="p1", resume_score=80),
        MagicMock(name="p2", resume_score=70),
        MagicMock(name="p3", resume_score=60),
    ]

    with patch("builtins.input", return_value="1,3"):
        selected = analyzer_base._select_multiple_projects(projects)

    assert selected == [projects[0], projects[2]]


def test_select_multiple_projects_cancel(analyzer_base):
    with patch("builtins.input", return_value="q"):
        assert analyzer_base._select_multiple_projects(
            [MagicMock(resume_score=80)]
        ) is None


def test_select_multiple_projects_invalid_then_valid(analyzer_base):
    projects = [
        MagicMock(name="p1", resume_score=80),
        MagicMock(name="p2", resume_score=70),
    ]

    with patch("builtins.input", side_effect=["99", "1"]):
        selected = analyzer_base._select_multiple_projects(projects)

    assert selected == [projects[0]]


