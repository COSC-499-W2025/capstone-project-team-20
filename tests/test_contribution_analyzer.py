import pytest
from unittest.mock import MagicMock, patch
from src.analyzers.ContributionAnalyzer import ContributionAnalyzer, ContributionStats

@pytest.fixture
def analyzer():
    return ContributionAnalyzer()

@pytest.fixture
def mock_repo():
    """Create a mock Git repository with commits"""
    repo = MagicMock()
    return repo

def create_mock_commit(author_name, files_changed):
    """Helper to create mock commit with file stats"""
    commit = MagicMock()
    commit.author.name = author_name
    commit.stats.files = files_changed
    return commit

# Tests for get_all_authors
def test_get_all_authors_single_author(analyzer):
    mock_commit = create_mock_commit("Alice", {})
    with patch("src.analyzers.ContributionAnalyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = [mock_commit]
        result = analyzer.get_all_authors("/fake/path")
    assert result == ["Alice"]

def test_get_all_authors_multiple_authors(analyzer):
    commits = [
        create_mock_commit("Bob", {}),
        create_mock_commit("Alice", {}),
        create_mock_commit("Charlie", {})
    ]
    with patch("src.analyzers.ContributionAnalyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = commits
        result = analyzer.get_all_authors("/fake/path")
    assert result == ["Alice", "Bob", "Charlie"]

def test_get_all_authors_duplicate_names(analyzer):
    """Test that duplicate author names are deduplicated"""
    commits = [
        create_mock_commit("Alice", {}),
        create_mock_commit("Alice", {}),
        create_mock_commit("Bob", {})
    ]
    with patch("src.analyzers.ContributionAnalyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = commits
        result = analyzer.get_all_authors("/fake/path")
    assert result == ["Alice", "Bob"]

def test_get_all_authors_empty_repo(analyzer):
    with patch("src.analyzers.ContributionAnalyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = []
        result = analyzer.get_all_authors("/fake/path")
    assert result == []

# Tests for analyze
def test_analyze_single_author(analyzer):
    files_changed = {
        "src/main.py": {"insertions": 10, "deletions": 5},
        "README.md": {"insertions": 3, "deletions": 1}
    }
    commit = create_mock_commit("Alice", files_changed)
    with patch("src.analyzers.ContributionAnalyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = [commit]
        result = analyzer.analyze("/fake/path")

    assert "Alice" in result
    alice_stats = result["Alice"]
    assert alice_stats.lines_added == 13
    assert alice_stats.lines_deleted == 6
    assert alice_stats.total_commits == 1
    assert len(alice_stats.files_touched) == 2

def test_analyze_multiple_authors(analyzer):
    commits = [
        create_mock_commit("Alice", {"file1.py": {"insertions": 10, "deletions": 2}}),
        create_mock_commit("Bob", {"file2.py": {"insertions": 5, "deletions": 3}})
    ]
    with patch("src.analyzers.ContributionAnalyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = commits
        result = analyzer.analyze("/fake/path")

    assert len(result) == 2
    assert "Alice" in result
    assert "Bob" in result
    assert result["Alice"].lines_added == 10
    assert result["Bob"].lines_added == 5

def test_analyze_accumulates_multiple_commits(analyzer):
    commits = [
        create_mock_commit("Alice", {"file1.py": {"insertions": 10, "deletions": 2}}),
        create_mock_commit("Alice", {"file2.py": {"insertions": 5, "deletions": 1}})
    ]
    with patch("src.analyzers.ContributionAnalyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = commits
        result = analyzer.analyze("/fake/path")

    assert result["Alice"].lines_added == 15
    assert result["Alice"].lines_deleted == 3
    assert result["Alice"].total_commits == 2

# Tests for file categorization
def test_categorize_file_path_code(analyzer):
    assert analyzer._categorize_file_path("src/main.py") == "code"
    assert analyzer._categorize_file_path("lib/utils.js") == "code"

def test_categorize_file_path_test(analyzer):
    assert analyzer._categorize_file_path("test/test_main.py") == "test"
    assert analyzer._categorize_file_path("tests/unit/test_utils.py") == "test"

def test_categorize_file_path_docs(analyzer):
    assert analyzer._categorize_file_path("doc/README.md") == "docs"
    assert analyzer._categorize_file_path("docs/guide.md") == "docs"

def test_categorize_file_path_case_insensitive(analyzer):
    assert analyzer._categorize_file_path("TEST/file.py") == "test"
    assert analyzer._categorize_file_path("DOCS/file.md") == "docs"

def test_analyze_categorizes_contributions(analyzer):
    files_changed = {
        "src/main.py": {"insertions": 10, "deletions": 0},
        "test/test_main.py": {"insertions": 5, "deletions": 0},
        "docs/README.md": {"insertions": 3, "deletions": 0}
    }
    commit = create_mock_commit("Alice", files_changed)
    with patch("src.analyzers.ContributionAnalyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = [commit]
        result = analyzer.analyze("/fake/path")

    alice_stats = result["Alice"]
    assert alice_stats.contribution_by_type["code"] == 10
    assert alice_stats.contribution_by_type["test"] == 5
    assert alice_stats.contribution_by_type["docs"] == 3

# Tests for ContributionStats
def test_contribution_stats_to_dict():
    stats = ContributionStats(
        lines_added=10,
        lines_deleted=5,
        total_commits=3,
        files_touched={"file1.py", "file2.py"},
        contribution_by_type={"code": 15, "test": 5, "docs": 0}
    )
    result = stats.to_dict()
    assert result["lines_added"] == 10
    assert result["files_touched"] == ["file1.py", "file2.py"]
    assert isinstance(result["files_touched"], list)

def test_contribution_stats_empty():
    stats = ContributionStats()
    assert stats.lines_added == 0
    assert stats.lines_deleted == 0
    assert stats.total_commits == 0
    assert len(stats.files_touched) == 0
    assert stats.contribution_by_type == {"code": 0, "docs": 0, "test": 0}
