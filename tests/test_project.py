import pytest
from datetime import datetime
from src.Project import Project
import json

@pytest.fixture
def sample_project():
    return Project(
        name="TestProject",
        file_path="/path/to/project/main.py",
        root_folder="/path/to/project",
        num_files=5,
        size_kb=12345,
        authors=["Alice", "Bob"],
        languages=["Python", "R"],
        frameworks=["PyTorch"],
        skills_used=["ML", "Data Analysis"],
        individual_contributions=["Feature extraction"],
        collaboration_status="collaborative",
        date_created=datetime(2025, 1, 1),
        last_modified=datetime(2025, 1, 5),
        last_accessed=datetime(2025, 1, 10)
    )

def test_project_to_dict_and_from_dict(sample_project):
    sample_project.update_author_count()
    d = sample_project.to_dict()
    
    # Ensure list fields are JSON strings
    for field in ["authors", "languages", "frameworks", "skills_used", "individual_contributions"]:
        assert isinstance(d[field], str)
        loaded = json.loads(d[field])
        assert isinstance(loaded, list)
    
    assert isinstance(d["collaboration_status"], str)

    assert d["collaboration_status"] in ["individual", "collaborative"]

    
    # Ensure dates are ISO strings
    for field in ["date_created", "last_modified", "last_accessed"]:
        value = getattr(sample_project, field)
        if value:
            assert isinstance(d[field], str)
    
    # Reconstruct object
    p2 = Project.from_dict(d)
    
    # Check all fields
    p2 = Project.from_dict(d)
    p2.update_author_count()
    assert p2.name == sample_project.name
    assert p2.file_path == sample_project.file_path
    assert p2.root_folder == sample_project.root_folder
    assert p2.num_files == sample_project.num_files
    assert p2.size_kb == sample_project.size_kb
    assert p2.authors == sample_project.authors
    assert p2.languages == sample_project.languages
    assert p2.frameworks == sample_project.frameworks
    assert p2.skills_used == sample_project.skills_used
    assert p2.individual_contributions == sample_project.individual_contributions
    assert p2.collaboration_status == sample_project.collaboration_status
    assert p2.date_created == sample_project.date_created
    assert p2.last_modified == sample_project.last_modified
    assert p2.last_accessed == sample_project.last_accessed
    assert p2.author_count == len(sample_project.authors)

