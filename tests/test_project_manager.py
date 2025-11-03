import pytest
import os
from datetime import datetime
from src.ProjectManager import ProjectManager
from src.Project import Project

DB_PATH = "test_projects.db"

@pytest.fixture
def cleanup_db():
    # Remove test DB if it exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    yield
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

@pytest.fixture
def sample_project():
    return Project(
        name="SampleProj",
        file_path="/proj/path/main.py",
        root_folder="/proj/path",
        num_files=3,
        size_kb=1024,
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

@pytest.fixture
def another_project():
    return Project(
        name="AnotherProj",
        file_path="/proj/other/main.py",
        root_folder="/proj/other",
        num_files=5,
        size_kb=2048,
        authors=[],
        languages=[],
        frameworks=[],
        skills_used=[],
        individual_contributions=[],
        collaboration_status="individual",
        date_created=None
    )

def test_set_and_get_project(cleanup_db, sample_project):
    manager = ProjectManager(DB_PATH)
    manager.set(sample_project)
    
    # Check that the id is set
    assert sample_project.id is not None
    
    # Retrieve and check all fields
    retrieved = manager.get(sample_project.id)
    assert retrieved.name == sample_project.name
    assert retrieved.file_path == sample_project.file_path
    assert retrieved.root_folder == sample_project.root_folder
    assert retrieved.num_files == sample_project.num_files
    assert retrieved.size_kb == sample_project.size_kb
    assert retrieved.authors == sample_project.authors
    assert retrieved.author_count == len(sample_project.authors)
    assert retrieved.languages == sample_project.languages
    assert retrieved.frameworks == sample_project.frameworks
    assert retrieved.skills_used == sample_project.skills_used
    assert retrieved.individual_contributions == sample_project.individual_contributions
    assert retrieved.collaboration_status == sample_project.collaboration_status
    assert retrieved.date_created == sample_project.date_created
    assert retrieved.last_modified == sample_project.last_modified
    assert retrieved.last_accessed == sample_project.last_accessed

def test_get_all_and_clear(cleanup_db, sample_project, another_project):
    manager = ProjectManager(DB_PATH)
    manager.set(sample_project)
    manager.set(another_project)
    
    all_projects = manager.get_all()
    assert len(all_projects) == 2
    names = [p['name'] for p in all_projects]
    assert "SampleProj" in names and "AnotherProj" in names
    
    # Clear DB and check empty
    manager.clear()
    assert manager.get_all() == []

def test_delete_project(cleanup_db, sample_project):
    manager = ProjectManager(DB_PATH)
    manager.set(sample_project)
    proj_id = sample_project.id
    
    # Delete project
    success = manager.delete(proj_id)
    assert success
    
    # Make sure it's gone
    assert manager.get(proj_id) is None
    assert manager.get_all() == []

def test_edge_cases_empty_lists_and_none(cleanup_db):
    project = Project(
        name="EmptyProj",
        file_path="",
        root_folder="",
        num_files=0,
        size_kb=0,
        authors=[],
        languages=[],
        frameworks=[],
        skills_used=[],
        individual_contributions=[],
        collaboration_status="individual",
        date_created=None,
        last_modified=None,
        last_accessed=None
    )
    manager = ProjectManager(DB_PATH)
    manager.set(project)
    
    retrieved = manager.get(project.id)
    assert retrieved.authors == []
    assert retrieved.author_count == 0
    assert retrieved.languages == []
    assert retrieved.frameworks == []
    assert retrieved.skills_used == []
    assert retrieved.individual_contributions == []
    assert retrieved.date_created is None
    assert retrieved.last_modified is None
    assert retrieved.last_accessed is None
    assert retrieved.collaboration_status == "individual"
