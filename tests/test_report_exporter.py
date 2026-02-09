import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
import subprocess  # <-- FIX: Added this import

from src.exporters.ReportExporter import ReportExporter
from src.models.Report import Report
from src.models.ReportProject import ReportProject, PortfolioDetails
from src.managers.ConfigManager import ConfigManager


# Fixtures
@pytest.fixture
def exporter():
    return ReportExporter()

@pytest.fixture
def mock_config_manager():
    """Mock ConfigManager with sample data."""
    config = MagicMock(spec=ConfigManager)
    config.get.side_effect = lambda key, default=None: {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "555-123-4567",
        "github": "johndoe",
        "linkedin": "johndoe"
    }.get(key, default)
    return config

@pytest.fixture
def sample_report():
    """A report with one detailed project."""
    proj = ReportProject(
        project_name="Awesome Project",
        bullets=["Did a thing"],
        summary="A great summary",
        portfolio_details=PortfolioDetails(overview="Overview text"),
        languages=["Python"],
        date_created=datetime.now()
    )
    return Report(title="My Report", projects=[proj])


# Tests
def test_export_to_pdf_success(exporter, sample_report, mock_config_manager, tmp_path, monkeypatch):
    """Tests a successful PDF generation workflow."""
    output_file = tmp_path / "output.pdf"
    mock_run = MagicMock()
    monkeypatch.setattr("subprocess.run", mock_run)

    exporter.export_to_pdf(sample_report, mock_config_manager, str(output_file), "jake")

    # Check that latexmk was called
    assert mock_run.call_count > 0
    args, _ = mock_run.call_args
    assert "latexmk" in args[0]
    assert f"-output-directory={tmp_path.resolve()}" in args[0]

def test_export_to_pdf_no_projects_raises_error(exporter, mock_config_manager, tmp_path):
    """Tests that exporting a report with no projects raises a ValueError."""
    empty_report = Report(title="Empty")
    with pytest.raises(ValueError, match="Cannot export a report with no projects"):
        exporter.export_to_pdf(empty_report, mock_config_manager, str(tmp_path / "out.pdf"), "jake")

def test_export_to_pdf_latex_not_found_raises_error(exporter, sample_report, mock_config_manager, tmp_path, monkeypatch):
    """Tests that a FileNotFoundError from subprocess is caught and re-raised."""
    monkeypatch.setattr("subprocess.run", MagicMock(side_effect=FileNotFoundError))
    with pytest.raises(RuntimeError, match="`latexmk` command not found"):
        exporter.export_to_pdf(sample_report, mock_config_manager, str(tmp_path / "out.pdf"), "jake")

@patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "latexmk", "output", "stderr"))
def test_export_to_pdf_latex_compilation_fails_raises_error(mock_run, exporter, sample_report, mock_config_manager, tmp_path):
    """Tests that a CalledProcessError from subprocess is caught and re-raised."""
    with pytest.raises(RuntimeError, match="LaTeX compilation failed"):
        exporter.export_to_pdf(sample_report, mock_config_manager, str(tmp_path / "out.pdf"), "jake")

def test_escape_latex_filter(exporter):
    """Tests the Jinja2 filter for escaping LaTeX special characters."""
    assert exporter._escape_latex_filter("a & b") == r"a \& b"
    assert exporter._escape_latex_filter("100%") == r"100\%"
    assert exporter._escape_latex_filter("path_name") == r"path\_name"
    assert exporter._escape_latex_filter(None) is None
    assert exporter._escape_latex_filter(123) == 123
