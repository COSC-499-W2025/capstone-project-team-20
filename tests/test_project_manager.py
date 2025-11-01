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
        root_folder="/proj/path",
        num_files=3,
        size=1024,
        languages=["Python", "R"],
        frameworks=["PyTorch"],
        skills_used=["ML", "Data Analysis"],
        individual_contributions=["Feature extraction"],
        date_created=datetime(2025, 1, 1),
        last_modified=datetime(2025, 1, 5),
        last_accessed=datetime(2025, 1, 10)
    )

@pytest.fixture
def another_project():
    return Project(
        name="AnotherProj",
        root_folder="/proj/other",
        num_files=5,
        size=2048,
        languages=[],
        frameworks=[],
        skills_used=[],
        individual_contributions=[],
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
    assert retrieved.num_files == sample_project.num_files
    assert retrieved.size == sample_project.size
    assert retrieved.languages == sample_project.languages
    assert retrieved.frameworks == sample_project.frameworks
    assert retrieved.skills_used == sample_project.skills_used
    assert retrieved.individual_contributions == sample_project.individual_contributions
    assert retrieved.date_created == sample_project.date_created
    assert retrieved.last_modified == sample_project.last_modified
    assert retrieved.last_accessed == sample_project.last_accessed

def test_get_all_and_clear(cleanup_db, sample_project, another_project):
    manager = ProjectManager(DB_PATH)
    manager.set(sample_project)
    manager.set(another_project)
    
    all_projects = list(manager.get_all())
    assert len(all_projects) == 2
    names = [p['name'] for p in all_projects]
    assert "SampleProj" in names and "AnotherProj" in names
    
    # Clear DB and check empty
    manager.clear()
    assert list(manager.get_all()) == []

def test_delete_project(cleanup_db, sample_project):
    manager = ProjectManager(DB_PATH)
    manager.set(sample_project)
    proj_id = sample_project.id
    
    # Delete project
    success = manager.delete(proj_id)
    assert success
    
    # Make sure it's gone
    assert manager.get(proj_id) is None
    assert list(manager.get_all()) == []

def test_edge_cases_empty_lists_and_none(cleanup_db):
    project = Project(
        name="EmptyProj",
        root_folder="",
        num_files=0,
        size=0,
        languages=[],
        frameworks=[],
        skills_used=[],
        individual_contributions=[],
        date_created=None,
        last_modified=None,
        last_accessed=None
    )
    manager = ProjectManager(DB_PATH)
    manager.set(project)
    
    retrieved = manager.get(project.id)
    assert retrieved.languages == []
    assert retrieved.frameworks == []
    assert retrieved.skills_used == []
    assert retrieved.individual_contributions == []
    assert retrieved.date_created is None
    assert retrieved.last_modified is None
    assert retrieved.last_accessed is None
