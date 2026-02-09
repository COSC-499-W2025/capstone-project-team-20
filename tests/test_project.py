import pytest
from datetime import datetime
from src.models.Project import Project
from src.models.ReportProject import PortfolioDetails
import json

@pytest.fixture
def sample_project():
    return Project(
        name="TestProject",
        file_path="/path/to/project/main.py",
        root_folder="/path/to/project",
        authors=["Alice", "Bob"],
        author_count=2,
        languages=["Python", "R"],
        date_created=datetime(2025, 1, 1)
    )

def test_project_to_dict_and_from_dict_roundtrip(sample_project: Project):
    """Tests that a project can be serialized and deserialized without data loss."""
    sample_project.skills_used = ["Docker", "CI/CD"]
    sample_project.portfolio_details = PortfolioDetails(project_name="TestProject", role="Lead Dev")
    project_dict = sample_project.to_dict()

    assert isinstance(project_dict['authors'], str)
    assert isinstance(project_dict['portfolio_details'], str)

    reconstructed_project = Project.from_dict(project_dict)

    assert reconstructed_project.name == sample_project.name
    assert reconstructed_project.authors == ["Alice", "Bob"]
    assert reconstructed_project.author_count == 2
    assert reconstructed_project.skills_used == ["Docker", "CI/CD"]
    assert isinstance(reconstructed_project.portfolio_details, PortfolioDetails)
    assert reconstructed_project.portfolio_details.role == "Lead Dev"

def test_project_display_shows_resume_score(sample_project, capsys):
    """Tests that the display method includes the formatted resume score."""
    sample_project.resume_score = 88.123
    sample_project.display()
    captured = capsys.readouterr()
    assert "(Resume Score: 88.12)" in captured.out
