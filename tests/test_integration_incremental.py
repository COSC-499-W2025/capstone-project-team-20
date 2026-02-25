"""
Integration tests for incremental ingestion and duplicate detection.
"""

from pathlib import Path
import pytest
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager
from src.ZipParser import parse_zip_to_project_folders
from unittest.mock import patch

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
    Use a temporary working directory so that projects.db, hashes.db,
    and any other stateful files are created fresh for each test.
    """
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def config(temp_cwd):
    return ConfigManager(db_path=str(temp_cwd / "config.db"))

def test_incremental_ingestion_updates_existing_project(
    temp_cwd, config, early_zip, late_zip
):
    early_analyzer = run_full_ingestion_for_zip(early_zip, config)
    all_after_early = list(early_analyzer.project_manager.get_all())
    assert len(all_after_early) == 1
    early_project = all_after_early[0]
    early_id = early_project.id
    early_num_files = early_project.num_files
    early_created = early_project.date_created

    late_analyzer = run_full_ingestion_for_zip(late_zip, config)
    all_after_late = list(late_analyzer.project_manager.get_all())
    assert len(all_after_late) == 1
    updated = all_after_late[0]

    assert updated.id == early_id
    assert updated.date_created == early_created
    assert updated.num_files >= early_num_files

def test_duplicate_files_detected_and_not_duplicated(
    temp_cwd, config, early_zip, late_zip
):
    early_analyzer = run_full_ingestion_for_zip(early_zip, config)
    early_project = list(early_analyzer.project_manager.get_all())[0]
    early_hashes = list(early_analyzer.file_hash_manager.get_all())
    assert len(early_hashes) > 0

    late_analyzer = run_full_ingestion_for_zip(late_zip, config)
    late_project = list(late_analyzer.project_manager.get_all())[0]
    late_hashes = list(late_analyzer.file_hash_manager.get_all())

    # late should have same or more hashes, never fewer
    assert len(late_hashes) >= len(early_hashes)

def test_uploading_older_zip_after_newer_does_not_downgrade(
    temp_cwd, config, early_zip, late_zip
):
    late_analyzer = run_full_ingestion_for_zip(late_zip, config)
    late_id = list(late_analyzer.project_manager.get_all())[0].id

    early_analyzer = run_full_ingestion_for_zip(early_zip, config)
    all_projects = list(early_analyzer.project_manager.get_all())

    assert len(all_projects) == 1
    assert all_projects[0].id == late_id

def test_project_id_stable_across_multiple_uploads(
    temp_cwd, config, early_zip, late_zip
):
    first = run_full_ingestion_for_zip(early_zip, config)
    original_id = list(first.project_manager.get_all())[0].id

    run_full_ingestion_for_zip(late_zip, config)
    run_full_ingestion_for_zip(early_zip, config)
    run_full_ingestion_for_zip(late_zip, config)

    final = run_full_ingestion_for_zip(late_zip, config)
    final_id = list(final.project_manager.get_all())[0].id

    assert final_id == original_id

def test_changed_file_triggers_update_path(
    temp_cwd, config, early_zip, late_zip
):
    early_analyzer = run_full_ingestion_for_zip(early_zip, config)
    early_path = list(early_analyzer.project_manager.get_all())[0].file_path

    original = ProjectAnalyzer._has_project_changed
    call_results = []

    def spy(self, project):
        result = original(self, project)
        call_results.append(result)
        return result

    with patch.object(ProjectAnalyzer, "_has_project_changed", spy):
        late_analyzer = run_full_ingestion_for_zip(late_zip, config)

    assert len(call_results) > 0
    assert any(call_results)  # at least one call returned True
    updated = list(late_analyzer.project_manager.get_all())[0]
    assert updated.file_path != early_path


def test_later_zip_metadata_reflected_after_update(
    temp_cwd, config, early_zip, late_zip
):
    early_analyzer = run_full_ingestion_for_zip(early_zip, config)
    early_project = list(early_analyzer.project_manager.get_all())[0]
    early_num_files = early_project.num_files

    late_analyzer = run_full_ingestion_for_zip(late_zip, config)
    updated = list(late_analyzer.project_manager.get_all())[0]

    # late zip has more files so num_files should reflect the late zip
    assert updated.num_files != early_num_files
    # file path should point to late extraction, not early
    assert updated.file_path != early_project.file_path


def test_analysis_results_preserved_on_incremental_upload(
    temp_cwd, config, early_zip, late_zip
):
    early_analyzer = run_full_ingestion_for_zip(early_zip, config)
    project = list(early_analyzer.project_manager.get_all())[0]

    # Simulate analysis results being present
    project.resume_score = 88.5
    project.skills_used = ["Python", "SQL"]
    project.bullets = ["Built a thing", "Improved a thing"]
    project.summary = "A great project"
    early_analyzer.project_manager.set(project)

    # Now upload the late zip
    late_analyzer = run_full_ingestion_for_zip(late_zip, config)
    updated = list(late_analyzer.project_manager.get_all())[0]

    # Analysis results should survive the incremental upload
    assert updated.resume_score == 88.5
    assert updated.skills_used == ["Python", "SQL"]
    assert updated.bullets == ["Built a thing", "Improved a thing"]
    assert updated.summary == "A great project"