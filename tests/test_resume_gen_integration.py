"""
Integration test that actually generates a PDF (no mocks).
Run this to verify the entire resume generation pipeline works.
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.exporters.ReportExporter import ReportExporter


class MockProject:
    """Simple mock project for testing"""
    def __init__(self):
        self.project_name = "Task Manager App"
        self.languages = ["Python", "JavaScript"]
        self.frameworks = ["Django", "React"]
        self.date_created = datetime(2024, 1, 15)
        self.last_modified = datetime(2024, 6, 20)
        self.bullets = [
            "Built a full-stack task management application with user authentication",
            "Implemented RESTful API with 20+ endpoints using Django REST Framework",
            "Designed responsive UI with React & Material-UI serving 500+ users",
            "Reduced page load time by 40% through code splitting and lazy loading"
        ]


class MockReport:
    """Simple mock report for testing"""
    def __init__(self):
        self.projects = [
            MockProject(),
            self._create_second_project()
        ]

    def _create_second_project(self):
        proj = MockProject()
        proj.project_name = "Weather Dashboard"
        proj.languages = ["TypeScript", "Python"]
        proj.frameworks = ["Next.js", "FastAPI"]
        proj.date_created = datetime(2023, 9, 1)
        proj.last_modified = datetime(2024, 3, 15)
        proj.bullets = [
            "Developed real-time weather tracking dashboard with live updates",
            "Integrated 5+ weather APIs with automatic failover system",
            "Implemented caching strategy reducing API calls by 80%"
        ]
        return proj


class MockConfig:
    """Simple mock config manager for testing"""
    def __init__(self):
        self.data = {
            "name": "Jane Developer",
            "email": "jane.dev@example.com",
            "phone": "555-123-4567",
            "github": "janedev",
            "linkedin": "jane-developer"
        }

    def get(self, key, default=None):
        return self.data.get(key, default)


# ============================================================
# Helpers
# ============================================================

def _assert_valid_pdf(path: Path):
    """Reusable check that a file exists and is a valid PDF."""
    assert path.exists(), f"PDF file was not created at {path}"
    assert path.stat().st_size > 0, "PDF file is empty"
    with open(path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-", f"File is not a valid PDF (got {header!r})"


def _extract_pdf_text(path: Path) -> str:
    """
    Extract text from a PDF using pdftotext (ships with most LaTeX installs).
    Returns empty string if pdftotext is not available.
    """
    try:
        result = subprocess.run(
            ["pdftotext", str(path), "-"],
            capture_output=True,
            text=True,
            timeout=15
        )
        return result.stdout
    except FileNotFoundError:
        return ""


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def exporter():
    return ReportExporter()


@pytest.fixture
def template_path():
    """Derive template location from the exporter module itself — stays correct
    regardless of where the test file lives."""
    import src.exporters.ReportExporter as mod
    return Path(mod.__file__).parent / "templates" / "jake.tex"


@pytest.fixture
def output_dir(tmp_path, monkeypatch):
    """
    ReportExporter hardcodes output into a resumes/ subdirectory relative to cwd.
    Redirect cwd to tmp_path so files land in a clean isolated location
    and are cleaned up automatically by pytest.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path / "resumes"


@pytest.fixture
def base_report():
    return MockReport()


@pytest.fixture
def base_config():
    return MockConfig()


# ============================================================
# Environment / setup tests
# ============================================================

def test_template_exists(template_path):
    assert template_path.exists(), (
        f"Template not found at {template_path}. "
        "You need to create the jake.tex template file!"
    )


def test_pdflatex_installed():
    try:
        result = subprocess.run(
            ["pdflatex", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0, "pdflatex returned non-zero exit code"
    except FileNotFoundError:
        pytest.skip(
            "pdflatex not installed. Install with:\n"
            "  macOS:  brew install --cask mactex-no-gui\n"
            "  Ubuntu: sudo apt-get install texlive-latex-base\n"
            "  Windows: https://miktex.org/download"
        )


# ============================================================
# Basic generation tests
# ============================================================

def test_basic_pdf_generation(output_dir, exporter, base_report, base_config):
    """Happy path — two projects, standard ASCII content."""
    exporter.export_to_pdf(base_report, base_config, "resume.pdf")
    _assert_valid_pdf(output_dir / "resume.pdf")


def test_pdf_generation_is_idempotent(output_dir, exporter, base_report, base_config):
    """Same input should always produce a valid PDF across multiple runs."""
    for i in range(3):
        exporter.export_to_pdf(base_report, base_config, f"run_{i}.pdf")
        _assert_valid_pdf(output_dir / f"run_{i}.pdf")


# ============================================================
# Special character tests
# ============================================================

def test_special_characters_in_bullets(output_dir, exporter, base_config):
    """LaTeX special characters in bullets must be escaped without crashing."""
    report = MockReport()
    report.projects[0].bullets = [
        "Reduced costs by $50,000 & improved performance by 100%",
        "Implemented O(n^2) -> O(n log n) optimization",
        "Handled edge_cases with user_names containing underscores",
        "Used ~50GB of memory for processing"
    ]
    exporter.export_to_pdf(report, base_config, "special_bullets.pdf")
    _assert_valid_pdf(output_dir / "special_bullets.pdf")


def test_special_characters_in_project_name(output_dir, exporter, base_config):
    """LaTeX special characters in the project name must be escaped."""
    report = MockReport()
    report.projects[0].project_name = "C++ & Database $ystem"
    exporter.export_to_pdf(report, base_config, "special_project_name.pdf")
    _assert_valid_pdf(output_dir / "special_project_name.pdf")


def test_special_characters_in_languages(output_dir, exporter, base_config):
    """Languages like C++ and C# must not break LaTeX rendering."""
    report = MockReport()
    report.projects[0].languages = ["C++", "C#", "F#"]
    exporter.export_to_pdf(report, base_config, "special_languages.pdf")
    _assert_valid_pdf(output_dir / "special_languages.pdf")


def test_special_characters_in_config(output_dir, exporter, base_report):
    """Ampersands or special chars in user config fields must be handled."""
    config = MockConfig()
    config.data["name"] = "Jane & John Developer"
    config.data["email"] = "jane+filter@example.com"
    exporter.export_to_pdf(base_report, config, "special_config.pdf")
    _assert_valid_pdf(output_dir / "special_config.pdf")


# ============================================================
# Edge case / boundary tests
# ============================================================

def test_single_project(output_dir, exporter, base_config):
    """A report with only one project should still generate correctly."""
    report = MockReport()
    report.projects = report.projects[:1]
    exporter.export_to_pdf(report, base_config, "single_project.pdf")
    _assert_valid_pdf(output_dir / "single_project.pdf")


def test_many_projects(output_dir, exporter, base_config):
    """Many projects should not overflow or crash the LaTeX template."""
    report = MockReport()
    report.projects = report.projects * 5
    exporter.export_to_pdf(report, base_config, "many_projects.pdf")
    _assert_valid_pdf(output_dir / "many_projects.pdf")


def test_empty_bullets_raises_validation_error(output_dir, exporter, base_config):
    """ReportExporter should reject projects with no bullets —
    they haven't been analyzed yet."""
    report = MockReport()
    report.projects[0].bullets = []
    with pytest.raises(ValueError, match="missing resume insights"):
        exporter.export_to_pdf(report, base_config, "no_bullets.pdf")


def test_empty_frameworks(output_dir, exporter, base_config):
    """A project with no frameworks should render without error,
    since languages alone satisfy the validator."""
    report = MockReport()
    report.projects[0].frameworks = []
    exporter.export_to_pdf(report, base_config, "no_frameworks.pdf")
    _assert_valid_pdf(output_dir / "no_frameworks.pdf")


def test_very_long_bullet(output_dir, exporter, base_config):
    """A very long bullet point should wrap gracefully rather than crash."""
    report = MockReport()
    report.projects[0].bullets = [
        "This is an extremely long bullet point that goes on and on and contains "
        "a great deal of information about a project that was very complex and "
        "required many different technologies and approaches to solve, including "
        "distributed systems, machine learning pipelines, and real-time data processing "
        "across multiple cloud providers simultaneously."
    ]
    exporter.export_to_pdf(report, base_config, "long_bullet.pdf")
    _assert_valid_pdf(output_dir / "long_bullet.pdf")


def test_pdf_size_scales_with_projects(output_dir, exporter, base_config):
    """A report with more projects should produce a larger PDF."""
    small_report = MockReport()
    small_report.projects = small_report.projects[:1]

    large_report = MockReport()
    large_report.projects = large_report.projects * 4

    exporter.export_to_pdf(small_report, base_config, "small.pdf")
    exporter.export_to_pdf(large_report, base_config, "large.pdf")

    assert (output_dir / "large.pdf").stat().st_size > (output_dir / "small.pdf").stat().st_size


# ============================================================
# Error handling tests
# ============================================================

def test_export_raises_on_invalid_output_path(exporter, base_report, base_config):
    """Passing a non-existent absolute directory should raise an error."""
    with pytest.raises(Exception):
        exporter.export_to_pdf(base_report, base_config, "/nonexistent/directory/resume.pdf")


# ============================================================
# Template extensibility tests
# ============================================================

@pytest.mark.parametrize("template_name", ["jake"])
def test_all_templates_exist(template_name):
    """Each registered template must have a corresponding .tex file.
    Add new template names to the parametrize list as they are created."""
    import src.exporters.ReportExporter as mod
    path = Path(mod.__file__).parent / "templates" / f"{template_name}.tex"
    assert path.exists(), f"Template not found: {path}"