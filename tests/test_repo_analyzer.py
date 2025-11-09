from pathlib import Path
from unittest.mock import MagicMock

import pytest
from git import Repo, Actor

# Import components to be tested or mocked
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from utils.RepoFinder import RepoFinder
from src.ProjectManager import ProjectManager
from src.Project import Project


@pytest.fixture
def create_real_repo(tmp_path: Path) -> Path:
    """
    Creates a real, temporary Git repository for testing the core analysis logic.
    """
    repo_path = tmp_path / "real_test_project"
    repo_path.mkdir()
    repo = Repo.init(repo_path)
    author1 = Actor("Real Author 1", "author1@real.com")
    author2 = Actor("Real Author 2", "author2@real.com")
    (repo_path / "file1.py").write_text("c1")
    repo.index.add(["file1.py"])
    repo.index.commit("commit 1", author=author1, committer=author1)
    (repo_path / "file2.py").write_text("c2")
    repo.index.add(["file2.py"])
    repo.index.commit("commit 2", author=author2, committer=author2)
    return repo_path


def test_analyzer_orchestration_workflow():
    """
    Unit tests the `run_analysis_from_path` method's orchestration logic.
    This test uses mocks to isolate the analyzer from its dependencies.
    """
    # Arrange: Create mocks for all external dependencies.
    mock_finder = MagicMock(spec=RepoFinder)
    mock_manager = MagicMock(spec=ProjectManager)

    # Configure mocks to simulate finding one existing project.
    repo_path = Path("/fake/repo")
    mock_finder.find_repos.return_value = [repo_path]

    existing_project = Project(id=123, name="repo")
    mock_manager.get_by_name.return_value = existing_project

    # Act: Instantiate the analyzer with mocks and run the workflow.
    analyzer = GitRepoAnalyzer(mock_finder, mock_manager)

    # Mock the internal analysis method to return predictable data.
    # This prevents the need for a real Git repo in this orchestration test.
    analyzer._analyze_and_prepare_project = MagicMock(return_value=existing_project)

    analyzer.run_analysis_from_path(Path("/any/path"))

    # Assert: Verify that the dependencies were called as expected.
    mock_finder.find_repos.assert_called_once()
    analyzer._analyze_and_prepare_project.assert_called_once_with(repo_path)
    mock_manager.set.assert_called_once_with(existing_project)


def test_analyzer_prepare_project_logic_for_new_project(create_real_repo: Path):
    """
    Unit tests the private `_analyze_and_prepare_project` method's logic
    for a project that does not yet exist in the database.
    """
    # Arrange
    mock_manager = MagicMock(spec=ProjectManager)
    mock_manager.get_by_name.return_value = None # Simulate project not found
    analyzer = GitRepoAnalyzer(repo_finder=None, project_manager=mock_manager)

    # Act
    project = analyzer._analyze_and_prepare_project(create_real_repo)

    # Assert
    assert project is not None
    assert project.id is None # ID should be None for a new project
    assert project.name == "real_test_project"
    assert project.author_count == 2
    assert project.collaboration_status == "collaborative"
    mock_manager.get_by_name.assert_called_once_with("real_test_project")

def test_analyzer_prepare_project_logic_for_existing_project(create_real_repo: Path):
    """
    Unit tests the `_analyze_and_prepare_project` method's logic
    for a project that already exists in the database.
    """
    # Arrange
    mock_manager = MagicMock(spec=ProjectManager)
    existing_project = Project(id=456, name="real_test_project", authors=["old_author"])
    mock_manager.get_by_name.return_value = existing_project # Simulate project found
    analyzer = GitRepoAnalyzer(repo_finder=None, project_manager=mock_manager)

    # Act
    project = analyzer._analyze_and_prepare_project(create_real_repo)

    # Assert
    assert project is not None
    # The existing ID should be preserved.
    assert project.id == 456
    # The author list and count should be updated by the new analysis.
    assert project.author_count == 2
    assert "author1@real.com" in project.authors
    assert "old_author" not in project.authors
    mock_manager.get_by_name.assert_called_once_with("real_test_project")
