from unittest.mock import patch, MagicMock
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.ConfigManager import ConfigManager
from src.Project import Project
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

    # FIX: Assert against the real, expected outcome
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

    # FIX: Assert against the real, expected outcome from parsing the good zip
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
