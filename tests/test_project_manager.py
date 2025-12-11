import pytest
import os
import sqlite3
import json
from datetime import datetime
from src.managers.ProjectManager import ProjectManager
from src.models.Project import Project

DB_PATH = "test_projects.db"

@pytest.fixture
def cleanup_db():
    # This fixture ensures the database is clean before and after each test.
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    yield
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

@pytest.fixture
def sample_project():
    # A standard project fixture for testing.
    # Note: The `Project` model is now a pure data class without repo attributes.
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
    # Another standard project fixture.
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
    assert sample_project.id is not None
    retrieved = manager.get(sample_project.id)
    assert retrieved.name == sample_project.name
    assert retrieved.authors == sample_project.authors
    assert retrieved.author_count == 2

def test_get_all_and_clear(cleanup_db, sample_project, another_project):
    manager = ProjectManager(DB_PATH)
    manager.set(sample_project)
    manager.set(another_project)
    all_projects = list(manager.get_all())
    assert len(all_projects) == 2
    manager.clear()
    assert list(manager.get_all()) == []

def test_delete_project(cleanup_db, sample_project):
    manager = ProjectManager(DB_PATH)
    manager.set(sample_project)
    proj_id = sample_project.id
    success = manager.delete(proj_id)
    assert success
    assert manager.get(proj_id) is None

# Updated Tests for Upsert
def test_get_by_name(cleanup_db, sample_project):
    """
    Tests the `get_by_name` method to ensure it retrieves the correct project.
    """
    manager = ProjectManager(DB_PATH)
    manager.set(sample_project)
    retrieved = manager.get_by_name("SampleProj")
    assert retrieved is not None
    assert retrieved.id == sample_project.id
    assert retrieved.name == "SampleProj"
    assert manager.get_by_name("NonExistentProject") is None

def test_upsert_logic_on_set(cleanup_db, sample_project):
    """
    Tests that calling `set` on a project with an existing name updates
    (replaces) the record instead of creating a new one.
    """
    manager = ProjectManager(DB_PATH)
    # First set operation
    manager.set(sample_project)
    original_id = sample_project.id
    assert original_id is not None

    # Modify the project and set it again
    sample_project.authors.append("Charlie")
    sample_project.update_author_count()
    manager.set(sample_project)  # This should perform an update/replace

    # Retrieve the project and verify its state
    retrieved = manager.get(original_id)
    assert retrieved.author_count == 3
    assert "Charlie" in retrieved.authors

    # Verify no new record was created
    all_projects = list(manager.get_all())
    assert len(all_projects) == 1

def test_unique_name_constraint(cleanup_db, sample_project):
    """
    Verifies that the database schema enforces the UNIQUE constraint on 'name'.
    This is a low-level test to ensure data integrity at the DB level.
    """
    manager = ProjectManager(DB_PATH)
    # The manager's `set` method uses `INSERT OR REPLACE`, so a raw
    # `INSERT` is needed to test the constraint directly.
    with manager._get_connection() as conn:
        cursor = conn.cursor()
        # First insert is fine
        cursor.execute("INSERT INTO projects (name, file_path) VALUES (?, ?)", ("SampleProj", "/path"))

        # Attempting a second raw INSERT with the same name should fail.
        with pytest.raises(sqlite3.IntegrityError) as excinfo:
            cursor.execute("INSERT INTO projects (name, file_path) VALUES (?, ?)", ("SampleProj", "/other/path"))

        # Ref: pytest.raises checks that the expected exception was thrown.
        # https://docs.pytest.org/en/7.1.x/reference/reference.html#pytest-raises
        assert "UNIQUE constraint failed: projects.name" in str(excinfo.value)

def test_set_and_get_with_resume_score(cleanup_db, sample_project):
    """Tests that the resume_score is persisted correctly in the database."""
    manager = ProjectManager(DB_PATH)
    sample_project.resume_score = 99.9

    manager.set(sample_project)
    retrieved = manager.get(sample_project.id)

    assert retrieved is not None
    assert retrieved.resume_score == 99.9
