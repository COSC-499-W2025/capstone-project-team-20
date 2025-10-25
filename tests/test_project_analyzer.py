import os
import zipfile
from pathlib import Path

import pytest
from git import Repo, Actor

from src.ProjectAnalyzer import ProjectAnalyzer


@pytest.fixture
def create_test_repo(tmp_path: Path) -> Path:
    """
    A pytest fixture to create a temporary Git repository for testing.

    This fixture sets up a Git repository, creates a source file, and
    simulates a commit history with both single-author and collaborative
    contributions. This provides a realistic test case for analysis.

    Args:
        tmp_path: The pytest fixture for a temporary directory path.

    Returns:
        The path to the root of the created Git repository.
    """
    repo_path = tmp_path / "test_project"
    repo_path.mkdir()
    repo = Repo.init(repo_path)

    # Define authors for commits
    author1 = Actor("Author One", "author1@example.com")
    author2 = Actor("Author Two", "author2@example.com")

    # Create and commit a file by the first author
    individual_file_path = repo_path / "individual_file.py"
    individual_file_path.write_text("print('hello from author one')")
    repo.index.add([str(individual_file_path)])
    repo.index.commit("Initial commit of individual file", author=author1, committer=author1)

    # Create a collaborative file and commit it
    collaborative_file_path = repo_path / "collaborative_file.py"
    collaborative_file_path.write_text("print('hello world')")
    repo.index.add([str(collaborative_file_path)])
    repo.index.commit("Initial commit", author=author1, committer=author1)

    # Modify the collaborative file as the second author
    collaborative_file_path.write_text("print('hello world, now updated')")
    repo.index.add([str(collaborative_file_path)])
    repo.index.commit("Second commit", author=author2, committer=author2)

    return repo_path


def test_analyze_zip_full_scenario(create_test_repo: Path, capsys):
    """
    Tests the ProjectAnalyzer's zip analysis functionality from end to end.

    This test verifies that the analyzer correctly identifies projects within a
    zip archive, analyzes the Git history of each file, and produces the
    expected human-readable output for both individual and collaborative files.

    Args:
        create_test_repo: The fixture that provides a path to a test repository.
        capsys: The pytest fixture for capturing stdout and stderr.
    """
    repo_path = create_test_repo
    tmp_dir = repo_path.parent
    zip_path = tmp_dir / "test_project.zip"

    # Create a zip archive from the repository directory
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(repo_path):
            for file in files:
                file_path = Path(root) / file
                archive_path = file_path.relative_to(repo_path.parent)
                zf.write(file_path, archive_path)

    # Initialize and run the analyzer
    analyzer = ProjectAnalyzer()
    analyzer.analyze_zip(str(zip_path))

    # Verify the console output
    captured = capsys.readouterr()
    output = captured.out

    # Check for correct project identification and analysis summary
    assert "Project: test_project" in output
    # Verify analysis of the collaborative file
    assert "File: collaborative_file.py" in output
    assert "Authors: 2" in output
    assert "Status: collaborative" in output
    # Verify analysis of the individual file
    assert "File: individual_file.py" in output
    assert "Authors: 1" in output
    assert "Status: individual" in output

    # Verify the internal state of the analyzer
    results = analyzer.get_analysis_results()
    assert len(results) == 2

    collaborative_result = next((r for r in results if r['file_path'] == 'collaborative_file.py'), None)
    individual_result = next((r for r in results if r['file_path'] == 'individual_file.py'), None)

    assert collaborative_result is not None
    assert collaborative_result['analysis_data']['author_count'] == 2
    assert collaborative_result['analysis_data']['collaboration_status'] == 'collaborative'

    assert individual_result is not None
    assert individual_result['analysis_data']['author_count'] == 1
    assert individual_result['analysis_data']['collaboration_status'] == 'individual'
