import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.models.Report import Report
from src.models.ReportProject import ReportProject

@pytest.fixture
def analyzer():
    """Provides a ProjectAnalyzer instance with mocked dependencies."""
    config_manager = MagicMock()
    # Mock the return for config checks to prevent ValueErrors
    config_manager.get.return_value = "configured"

    analyzer_instance = ProjectAnalyzer(config_manager=config_manager, zip_path=Path("/dummy.zip"))
    analyzer_instance.report_manager = MagicMock()
    analyzer_instance.report_exporter = MagicMock()
    return analyzer_instance

def test_get_and_refresh_report_create_new(analyzer: ProjectAnalyzer, monkeypatch):
    """Tests the 'create new report' flow within the PDF generation menu."""
    monkeypatch.setattr("builtins.input", lambda _: "n") # Choose 'n' for new

    # Mock the create_report flow which is called internally
    mock_create_report = MagicMock(return_value=Report(id=1, title="New Report"))
    monkeypatch.setattr(analyzer, "create_report", mock_create_report)

    report = analyzer._get_and_refresh_report()

    mock_create_report.assert_called_once()
    assert report is not None
    assert report.id == 1

def test_get_and_refresh_report_use_existing(analyzer: ProjectAnalyzer, monkeypatch):
    """Tests the 'use existing report' flow."""
    # Mock existing reports
    analyzer.report_manager.list_reports.return_value = [Report(id=5, title="Existing")]
    analyzer.report_manager.get_report.return_value = Report(id=5, title="Existing")

    # Simulate user choosing 'e' for existing, then entering ID '5'
    inputs = iter(["e", "5"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    report = analyzer._get_and_refresh_report()

    analyzer.report_manager.list_reports.assert_called_once()
    analyzer.report_manager.get_report.assert_called_once_with(5)
    assert report is not None
    assert report.id == 5

def test_trigger_resume_generation_success(analyzer: ProjectAnalyzer, monkeypatch):
    """Tests the happy path for triggering resume generation."""
    # Setup mocks
    mock_report = Report(id=1, title="Test Report", projects=[ReportProject(project_name="p1", bullets=["b"], summary="s")])
    monkeypatch.setattr(analyzer, "_get_and_refresh_report", MagicMock(return_value=mock_report))
    monkeypatch.setattr(analyzer, "_execute_pdf_generation", MagicMock())

    analyzer.trigger_resume_generation()

    # Verify that the final execution step was called correctly
    analyzer._execute_pdf_generation.assert_called_once_with(mock_report, "resume", analyzer._generate_resume)

def test_trigger_portfolio_generation_success(analyzer: ProjectAnalyzer, monkeypatch):
    """Tests the happy path for triggering portfolio generation."""
    mock_project = ReportProject(project_name="p1")
    # Mark portfolio_details as generated
    mock_project.portfolio_details.project_name = "p1"
    mock_report = Report(id=1, title="Test Report", projects=[mock_project])

    monkeypatch.setattr(analyzer, "_get_and_refresh_report", MagicMock(return_value=mock_report))
    monkeypatch.setattr(analyzer, "_execute_pdf_generation", MagicMock())

    analyzer.trigger_portfolio_generation()

    analyzer._execute_pdf_generation.assert_called_once_with(mock_report, "portfolio", analyzer._generate_portfolio)

def test_trigger_resume_generation_handles_missing_insights(analyzer: ProjectAnalyzer, monkeypatch, capsys):
    """Tests that generation is blocked if a project is missing resume insights."""
    # Project is missing bullets/summary
    mock_report = Report(id=1, title="Test Report", projects=[ReportProject(project_name="p1")])
    monkeypatch.setattr(analyzer, "_get_and_refresh_report", MagicMock(return_value=mock_report))

    analyzer.trigger_resume_generation()

    captured = capsys.readouterr()
    assert "Projects missing resume insights" in captured.out
    assert "p1" in captured.out
