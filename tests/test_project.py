import pytest
from datetime import datetime
from src.Project import Project
import json

@pytest.fixture
def sample_project():
    return Project(
        name="TestProject",
        root_folder="/path/to/project",
        num_files=5,
        size=12345,
        languages=["Python", "R"],
        frameworks=["PyTorch"],
        skills_used=["ML", "Data Analysis"],
        individual_contributions=["Feature extraction"],
        date_created=datetime(2025, 1, 1),
        last_modified=datetime(2025, 1, 5),
        last_accessed=datetime(2025, 1, 10)
    )

def test_project_to_dict_and_from_dict(sample_project):
    d = sample_project.to_dict()
    
    # Ensure lists are JSON strings
    for field in ["languages", "frameworks", "skills_used", "individual_contributions"]:
        assert isinstance(d[field], str)
        loaded = json.loads(d[field])
        assert isinstance(loaded, list)
    
    # Ensure dates are ISO strings
    for field in ["date_created", "last_modified", "last_accessed"]:
        if getattr(sample_project, field):
            assert isinstance(d[field], str)
    
    # Reconstruct object
    p2 = Project.from_dict(d)
    assert p2.name == sample_project.name
    assert p2.languages == sample_project.languages
    assert p2.date_created == sample_project.date_created
