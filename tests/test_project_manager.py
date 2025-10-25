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
        languages=["Python"],
        frameworks=[],
        skills_used=[],
        individual_contributions=[],
        date_created=datetime(2025, 1, 1)
    )

def test_set_and_get_project(cleanup_db, sample_project):
    manager = ProjectManager(DB_PATH)
    manager.set(sample_project)
    
    # Check that the id is set
    assert sample_project.id is not None
    
    retrieved = manager.get(sample_project.id)
    assert retrieved.name == sample_project.name
    assert retrieved.num_files == sample_project.num_files

def test_get_all_and_clear(cleanup_db, sample_project):
    manager = ProjectManager(DB_PATH)
    manager.set(sample_project)
    all_projects = manager.get_all()
    assert len(all_projects) == 1
    
    manager.clear()
    assert manager.get_all() == []
