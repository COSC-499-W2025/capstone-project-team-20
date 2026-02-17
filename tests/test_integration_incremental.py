"""
Integration tests for incremental ingestion and duplicate detection.
"""

from pathlib import Path
import pytest

from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager
from src.managers.ProjectManager import ProjectManager
from src.managers.FileHashManager import FileHashManager
from src.ZipParser import parse_zip_to_project_folders


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def run_full_ingestion_for_zip(zip_path: Path, config: ConfigManager) -> ProjectAnalyzer:
    root_folders = parse_zip_to_project_folders(zip_path)
    analyzer = ProjectAnalyzer(config, root_folders, zip_path)
    analyzer.initialize_projects()
    return analyzer


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest.fixture
def early_zip():
    return Path(__file__).parent.parent / "testResources" / "earlyProject.zip"

@pytest.fixture
def late_zip():
    return Path(__file__).parent.parent / "testResources" / "lateProject.zip"


@pytest.fixture
def temp_cwd(tmp_path, monkeypatch):
    """
    Use a temporary working directory so that:
    - projects.db
    - hashes.db
    - any other stateful files
    are created fresh for each test.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def config(temp_cwd):
    return ConfigManager(db_path=str(temp_cwd / "config.db"))


@pytest.fixture
def project_manager(temp_cwd):
    return ProjectManager(db_path=str(temp_cwd / "projects.db"))


@pytest.fixture
def file_hash_manager(temp_cwd):
    return FileHashManager(db_path=str(temp_cwd / "hashes.db"))


# ----------------------------------------------------------------------
# Test 1: Incremental ingestion updates existing project
# ----------------------------------------------------------------------

def test_incremental_ingestion_updates_existing_project(
    temp_cwd, config, project_manager, file_hash_manager, early_zip, late_zip
):
    # --- First run: early snapshot ---
    early_analyzer = run_full_ingestion_for_zip(early_zip, config)

    all_after_early = list(project_manager.get_all())
    assert len(all_after_early) == 1
    early_project = all_after_early[0]

    early_id = early_project.id
    early_num_files = early_project.num_files
    early_created = early_project.date_created
    early_modified = early_project.last_modified

    # --- Second run: late snapshot ---
    late_analyzer = run_full_ingestion_for_zip(late_zip, config)

    all_after_late = list(project_manager.get_all())
    assert len(all_after_late) == 1, "Should still have exactly one project"

    updated = all_after_late[0]

    # Same project (incremental update)
    assert updated.id == early_id

    # Creation date preserved
    assert updated.date_created == early_created

    # Last modified should be same or newer
    if early_modified and updated.last_modified:
        assert updated.last_modified >= early_modified

    # File count should not shrink
    assert updated.num_files >= early_num_files


# ----------------------------------------------------------------------
# Test 2: Duplicate file detection across snapshots
# ----------------------------------------------------------------------

def test_duplicate_files_detected_and_not_duplicated(
    temp_cwd, config, project_manager, file_hash_manager, early_zip, late_zip
):
    # --- First run: early snapshot ---
    early_analyzer = run_full_ingestion_for_zip(early_zip, config)
    early_project = list(project_manager.get_all())[0]

    early_stats = early_analyzer._register_project_files(early_project)
    assert early_stats["new"] > 0
    assert early_stats["duplicate"] == 0

    # --- Second run: late snapshot ---
    late_analyzer = run_full_ingestion_for_zip(late_zip, config)
    late_project = list(project_manager.get_all())[0]

    late_stats = late_analyzer._register_project_files(late_project)

    assert late_stats["duplicate"] > 0
    assert late_stats["new"] >= 0
