from datetime import datetime
from unittest.mock import patch, MagicMock
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.managers.ConfigManager import ConfigManager
from src.managers.ProjectManager import ProjectManager
from src.managers.FileHashManager import FileHashManager
from src.models.Project import Project
from src.models.ReportProject import PortfolioDetails
from src.ZipParser import parse_zip_to_project_folders
from src.ProjectFolder import ProjectFolder
from pathlib import Path
import pytest
import zipfile

# Fixtures
@pytest.fixture
def mock_config_manager():
    return MagicMock(spec=ConfigManager)

@pytest.fixture
def analyzer(mock_config_manager):
    dummy_zip = Path("/dummy/path.zip")
    # Start with empty root_folders, as they are loaded by load_zip
    return ProjectAnalyzer(
        config_manager=mock_config_manager,
        root_folders=[],
        zip_path=dummy_zip
    )

def test_load_zip_success(tmp_path):
    """Test that a successful parse returns the correct ProjectFolder objects."""
    # Create a real, temporary zip file for the test
    zip_location = tmp_path / "fake.zip"
    with zipfile.ZipFile(zip_location, 'w') as zf:
        zf.writestr("project-a/file.txt", "content")

    # Mock user input to provide the path to our real temp zip
    with patch("builtins.input", return_value=str(zip_location)):
        root_folders, _ = ProjectAnalyzer.load_zip()

    assert len(root_folders) == 1
    assert isinstance(root_folders[0], ProjectFolder)
    assert root_folders[0].name == 'project-a'

def test_load_zip_retry_then_success(tmp_path):
    """Test that the load function retries and then succeeds with a real file."""
    # Create the valid zip file
    good_zip_location = tmp_path / "good.zip"
    with zipfile.ZipFile(good_zip_location, 'w') as zf:
        zf.writestr("project-b/file.txt", "content")

    # Simulate user typing a bad path, then the good one
    inputs = iter(["/tmp/bad.zip", str(good_zip_location)])

    with patch("builtins.input", side_effect=inputs):
        root_folders, _ = ProjectAnalyzer.load_zip()

    assert len(root_folders) == 1
    assert isinstance(root_folders[0], ProjectFolder)
    assert root_folders[0].name == 'project-b'

def test_change_selected_users_workflow(analyzer, mock_config_manager):
    """Test the full workflow for changing selected users."""
    with patch.object(analyzer, '_get_projects', return_value=[Project(name="repo1", file_path="/fake/repo1")]), \
         patch("pathlib.Path.exists", return_value=True), \
         patch.object(analyzer.contribution_analyzer, 'get_all_authors', return_value=["Alice", "Bob"]), \
         patch.object(analyzer, '_prompt_for_usernames', return_value=["Bob"]) as mock_prompt:

        analyzer.change_selected_users()

        mock_prompt.assert_called_once_with(["Alice", "Bob"])
        mock_config_manager.set.assert_called_once_with("usernames", ["Bob"])

def test_initialize_projects_skips_older_zip_update(tmp_path, mock_config_manager):
    zip_location = tmp_path / "older.zip"
    with zipfile.ZipFile(zip_location, 'w') as zf:
        info = zipfile.ZipInfo("project-a/file.txt")
        info.date_time = datetime(2023, 1, 1).timetuple()[:6]
        zf.writestr(info, "content")

    root_folders = parse_zip_to_project_folders(str(zip_location))
    analyzer = ProjectAnalyzer(mock_config_manager, root_folders, zip_location)
    analyzer.project_manager = ProjectManager(db_path=str(tmp_path / "projects.db"))

    existing = Project(
        name="project-a",
        file_path="/old/path",
        root_folder="project-a",
        last_modified=datetime(2024, 1, 1),
    )
    analyzer.project_manager.set(existing)

    with patch.object(analyzer, "ensure_cached_dir", return_value=tmp_path), \
         patch("src.analyzers.ProjectAnalyzer.RepoProjectBuilder.scan", return_value=[
             Project(name="project-a", file_path="/new/path", root_folder="project-a")
         ]):
        analyzer.initialize_projects()

    updated = analyzer.project_manager.get_by_name("project-a")
    assert updated.file_path == "/old/path"
    assert updated.last_modified == datetime(2024, 1, 1)

def test_initialize_projects_updates_newer_zip(tmp_path, mock_config_manager):
    zip_location = tmp_path / "newer.zip"
    with zipfile.ZipFile(zip_location, 'w') as zf:
        info = zipfile.ZipInfo("project-b/file.txt")
        info.date_time = datetime(2024, 1, 1).timetuple()[:6]
        zf.writestr(info, "content")

    root_folders = parse_zip_to_project_folders(str(zip_location))
    analyzer = ProjectAnalyzer(mock_config_manager, root_folders, zip_location)
    analyzer.project_manager = ProjectManager(db_path=str(tmp_path / "projects.db"))

    existing = Project(
        name="project-b",
        file_path="/old/path",
        root_folder="project-b",
        last_modified=datetime(2023, 1, 1),
    )
    analyzer.project_manager.set(existing)

    with patch.object(analyzer, "ensure_cached_dir", return_value=tmp_path), \
         patch("src.analyzers.ProjectAnalyzer.RepoProjectBuilder.scan", return_value=[
             Project(name="project-b", file_path="/new/path", root_folder="project-b")
         ]):
        analyzer.initialize_projects()

    updated = analyzer.project_manager.get_by_name("project-b")
    assert updated.file_path == "/new/path"
    assert updated.last_modified.date() == datetime(2024, 1, 1).date()

def test_initialize_projects_does_not_duplicate_projects(tmp_path, mock_config_manager):
    zip_location = tmp_path / "same.zip"
    with zipfile.ZipFile(zip_location, 'w') as zf:
        zf.writestr("project-c/file.txt", "content")

    root_folders = parse_zip_to_project_folders(str(zip_location))
    analyzer = ProjectAnalyzer(mock_config_manager, root_folders, zip_location)
    analyzer.project_manager = ProjectManager(db_path=str(tmp_path / "projects.db"))

    with patch.object(analyzer, "ensure_cached_dir", return_value=tmp_path), \
         patch("src.analyzers.ProjectAnalyzer.RepoProjectBuilder.scan", return_value=[
             Project(name="project-c", file_path="/path", root_folder="project-c")
         ]):
        analyzer.initialize_projects()
        analyzer.initialize_projects()

    projects = list(analyzer.project_manager.get_all())
    assert len(projects) == 1

def test_register_project_files_dedupes_across_uploads(tmp_path, mock_config_manager):
    project_a_dir = tmp_path / "project-a"
    project_b_dir = tmp_path / "project-b"
    project_a_dir.mkdir()
    project_b_dir.mkdir()

    content = "same file contents"
    (project_a_dir / "file.txt").write_text(content)
    (project_b_dir / "file.txt").write_text(content)

    analyzer = ProjectAnalyzer(mock_config_manager, [], tmp_path / "dummy.zip")
    analyzer.file_hash_manager = FileHashManager(db_path=str(tmp_path / "files.db"))

    proj_a = Project(name="project-a", file_path=str(project_a_dir))
    proj_b = Project(name="project-b", file_path=str(project_b_dir))

    result_a = analyzer._register_project_files(proj_a)
    result_b = analyzer._register_project_files(proj_b)

    assert result_a["new"] == 1
    assert result_a["duplicate"] == 0
    assert result_b["new"] == 0
    assert result_b["duplicate"] == 1

    all_hashes = list(analyzer.file_hash_manager.get_all())
    assert len(all_hashes) == 1

def test_delete_previous_insights_clears_portfolio_details(analyzer):
    project = Project(name="demo", file_path="/tmp/demo")
    project.portfolio_details = PortfolioDetails(project_name="demo")
    analyzer.project_manager = MagicMock()
    analyzer.project_manager.get_all.return_value = [project]

    with patch.object(analyzer, "_select_project", return_value=project):
        analyzer.delete_previous_insights()

    assert project.portfolio_details.project_name == ""
