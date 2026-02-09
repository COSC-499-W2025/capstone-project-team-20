from datetime import datetime
from unittest.mock import patch, MagicMock
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager
from src.managers.ProjectManager import ProjectManager
from src.models.Project import Project
from src.ZipParser import parse_zip_to_project_folders
from src.ProjectFolder import ProjectFolder
from pathlib import Path
import pytest
import zipfile

def test_load_zip_success(tmp_path):
    """Test that a successful parse returns the correct ProjectFolder objects."""
    zip_location = tmp_path / "fake.zip"
    with zipfile.ZipFile(zip_location, 'w') as zf:
        zf.writestr("project-a/file.txt", "content")

    with patch("builtins.input", return_value=str(zip_location)):
        analyzer = ProjectAnalyzer(MagicMock(), [], None)
        root_folders, _ = analyzer.load_zip()

    assert len(root_folders) == 1
    assert isinstance(root_folders[0], ProjectFolder)
    assert root_folders[0].name == 'project-a'


def test_initialize_projects_updates_newer_zip(tmp_path):
    """
    Tests that if the DB has an older version of a project,
    initialize_projects will update its metadata from the newer zip.
    """
    zip_location = tmp_path / "newer.zip"
    with zipfile.ZipFile(zip_location, 'w') as zf:
        info = zipfile.ZipInfo("project-b/file.txt")
        info.date_time = (2024, 1, 1, 0, 0, 0)
        zf.writestr(info, "content")

    root_folders = parse_zip_to_project_folders(str(zip_location))
    analyzer = ProjectAnalyzer(MagicMock(), root_folders, zip_location)
    analyzer.project_manager = ProjectManager(db_path=str(tmp_path / "projects.db"))

    existing = Project(name="project-b", file_path="/old/path", last_modified=datetime(2023, 1, 1))
    analyzer.project_manager.set(existing)

    new_project_from_scan = Project(name="project-b", file_path="/new/path", root_folder="project-b", last_modified=datetime(2024, 1, 1))

    summary_mock = {
        "start_date": "2023-01-01",
        "end_date": "2024-01-01"
    }

    with patch.object(analyzer, "ensure_cached_dir", return_value=tmp_path), \
         patch("src.analyzers.ProjectAnalyzer.RepoProjectBuilder.scan", return_value=[new_project_from_scan]), \
         patch.object(analyzer, "_get_zip_project_summary", return_value=summary_mock):

        analyzer.initialize_projects()

    updated = analyzer.project_manager.get_by_name("project-b")

    assert updated.file_path == "/new/path"
    assert updated.last_modified is not None
    assert updated.last_modified.date() == datetime(2023, 1, 1).date()
