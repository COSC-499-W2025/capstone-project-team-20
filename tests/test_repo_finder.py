from pathlib import Path
import pytest
from utils.RepoFinder import RepoFinder

def test_repo_finder_discovers_repository(tmp_path: Path):
    """
    Unit test for the RepoFinder class.
    Verifies that the `find_repos` method correctly identifies a directory
    containing a `.git` subfolder.
    """
    # Arrange: Create a mock directory structure.
    project_path = tmp_path / "my_test_project"
    (project_path / ".git").mkdir(parents=True)
    (tmp_path / "empty_dir").mkdir() # An extra dir to ensure specificity.

    # Act
    finder = RepoFinder()
    repo_paths = finder.find_repos(tmp_path)

    # Assert
    assert len(repo_paths) == 1
    assert repo_paths[0] == project_path

def test_repo_finder_ignores_nested_repos(tmp_path: Path):
    """
    Verifies that RepoFinder correctly prunes its search and does not
    treat a submodule (a nested .git directory) as a second project.
    """
    # Arrange
    parent_path = tmp_path / "parent_project"
    (parent_path / ".git").mkdir(parents=True)
    submodule_path = parent_path / "libs" / "sub_project"
    (submodule_path / ".git").mkdir(parents=True)

    # Act
    finder = RepoFinder()
    repo_paths = finder.find_repos(tmp_path)

    # Assert
    assert len(repo_paths) == 1
    assert repo_paths[0] == parent_path

def test_repo_finder_handles_no_repos(tmp_path: Path):
    """
    Verifies that RepoFinder returns an empty list when no .git
    directory is found.
    """
    # Arrange
    (tmp_path / "project_without_git").mkdir()

    # Act
    finder = RepoFinder()
    repo_paths = finder.find_repos(tmp_path)

    # Assert
    assert len(repo_paths) == 0
