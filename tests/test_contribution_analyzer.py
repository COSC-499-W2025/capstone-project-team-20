import pytest
from unittest.mock import MagicMock, patch

from src.analyzers.contribution_analyzer import ContributionAnalyzer, ContributionStats


@pytest.fixture
def analyzer():
    a = ContributionAnalyzer()

    # ✅ Make tests deterministic: never ignore files unless a test explicitly wants that.
    a.file_categorizer.classify_file = MagicMock(return_value="code")

    # Optional but helpful: make language detection deterministic too
    a.file_categorizer.language_map = {
        "py": "Python",
        "md": "Markdown",
        "js": "JavaScript",
        "yml": "YAML",
    }
    return a


def create_mock_commit(author_name, files_changed, author_email="author@example.com", committer_name=None, committer_email=None):
    """Helper to create mock commit with file stats"""
    commit = MagicMock()
    commit.author.name = author_name
    commit.author.email = author_email
    commit.committer.name = committer_name or author_name
    commit.committer.email = committer_email or author_email
    commit.stats.files = files_changed
    commit.parents = [MagicMock()]  # ✅ ensures it is NOT treated as initial commit
    return commit


# -------------------------
# Tests for get_all_authors
# -------------------------

def test_get_all_authors_single_author(analyzer):
    mock_commit = create_mock_commit("Alice", "alice@example.com", {})
    with patch("src.analyzers.contribution_analyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = [mock_commit]
        result = analyzer.get_all_authors("/fake/path")
    assert result == {"alice@example.com": "Alice"}


def test_get_all_authors_multiple_authors(analyzer):
    commits = [
        create_mock_commit("Bob", "bob@example.com", {}),
        create_mock_commit("Alice", "alice@example.com", {}),
        create_mock_commit("Charlie", "charlie@example.com", {})
    ]
    with patch("src.analyzers.contribution_analyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = commits
        result = analyzer.get_all_authors("/fake/path")
    assert result == {
        "bob@example.com": "Bob",
        "alice@example.com": "Alice",
        "charlie@example.com": "Charlie"
    }

def test_get_all_authors_duplicate_emails_deduped(analyzer):
    """Test that commits from the same email are deduplicated, most recent name wins"""
    commits = [
        create_mock_commit("Alice New", "alice@example.com", {}),
        create_mock_commit("Alice Old", "alice@example.com", {}),
        create_mock_commit("Bob", "bob@example.com", {})
    ]
    with patch("src.analyzers.contribution_analyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = commits
        result = analyzer.get_all_authors("/fake/path")
    assert result["alice@example.com"] == "Alice New"
    assert result["bob@example.com"] == "Bob"
    assert len(result) == 2

def test_get_all_authors_same_name_different_emails(analyzer):
    """Test that same name with different emails are treated as different people"""
    commits = [
        create_mock_commit("Alice", "alice@example.com", {}),
        create_mock_commit("Alice", "alice@users.noreply.github.com", {}),
    ]
    with patch("src.analyzers.contribution_analyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = commits
        result = analyzer.get_all_authors("/fake/path")
    assert len(result) == 2
    assert "alice@example.com" in result
    assert "alice@users.noreply.github.com" in result


def test_get_all_authors_empty_repo(analyzer):
    with patch("src.analyzers.contribution_analyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = []
        result = analyzer.get_all_authors("/fake/path")
    assert result == {}

def test_get_all_authors_email_normalized_to_lowercase(analyzer):
    commits = [
        create_mock_commit("Alice", "Alice@Example.COM", {}),
    ]
    with patch("src.analyzers.contribution_analyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = commits
        result = analyzer.get_all_authors("/fake/path")
    assert "alice@example.com" in result


# -------------------------
# Tests for analyze
# -------------------------

def test_analyze_single_author(analyzer):
    files_changed = {
        "src/main.py": {"insertions": 10, "deletions": 5},
        "README.md": {"insertions": 3, "deletions": 1},
    }
    commit = create_mock_commit("Alice", "alice@example.com", files_changed)
    with patch("src.analyzers.contribution_analyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = [commit]
        result = analyzer.analyze("/fake/path")

    assert "alice@example.com" in result
    alice_stats = result["alice@example.com"]
    assert alice_stats.lines_added == 13
    assert alice_stats.lines_deleted == 6
    assert alice_stats.total_commits == 1
    assert len(alice_stats.files_touched) == 2


def test_analyze_multiple_authors(analyzer):
    commits = [
        create_mock_commit("Alice", "alice@example.com", {"file1.py": {"insertions": 10, "deletions": 2}}),
        create_mock_commit("Bob", "bob@example.com", {"file2.py": {"insertions": 5, "deletions": 3}})
    ]
    with patch("src.analyzers.contribution_analyzer.Repo") as MockRepo:  # ✅ FIXED PATCH PATH
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = commits
        result = analyzer.analyze("/fake/path")

    assert len(result) == 2
    assert "alice@example.com" in result
    assert "bob@example.com" in result
    assert result["alice@example.com"].lines_added == 10
    assert result["bob@example.com"].lines_added == 5


def test_analyze_accumulates_multiple_commits(analyzer):
    commits = [
        create_mock_commit("Alice", "alice@example.com", {"file1.py": {"insertions": 10, "deletions": 2}}),
        create_mock_commit("Alice", "alice@example.com", {"file2.py": {"insertions": 5, "deletions": 1}})
    ]
    with patch("src.analyzers.contribution_analyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = commits
        result = analyzer.analyze("/fake/path")

    assert result["alice@example.com"].lines_added == 15
    assert result["alice@example.com"].lines_deleted == 3
    assert result["alice@example.com"].total_commits == 2

def test_analyze_same_name_different_emails_tracked_separately(analyzer):
    """Two people with the same name but different emails should remain separate."""
    commits = [
        create_mock_commit("Alice", "alice@example.com", {"file1.py": {"insertions": 10, "deletions": 0}}),
        create_mock_commit("Alice", "alice@users.noreply.github.com", {"file2.py": {"insertions": 3, "deletions": 0}})
    ]
    with patch("src.analyzers.contribution_analyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = commits
        result = analyzer.analyze("/fake/path")

    assert len(result) == 2
    assert result["alice@example.com"].lines_added == 10
    assert result["alice@users.noreply.github.com"].lines_added == 3


# -------------------------
# Tests for file categorization
# -------------------------

def test_categorize_file_path_code(analyzer):
    assert analyzer._categorize_file_path("src/main.py") == "code"


def test_categorize_file_path_other_code(analyzer):
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
        "docs/README.md": {"insertions": 3, "deletions": 0},
        "config.yml": {"insertions": 2, "deletions": 0},
    }
    commit = create_mock_commit("Alice", "alice@example.com", files_changed)

    with patch("src.analyzers.contribution_analyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = [commit]
        result = analyzer.analyze("/fake/path")

    alice_stats = result["alice@example.com"]
    assert alice_stats.contribution_by_type["code"] == 10
    assert alice_stats.contribution_by_type["test"] == 5
    assert alice_stats.contribution_by_type["docs"] == 3
    assert alice_stats.contribution_by_type["other"] == 2

# Tests for _names_are_similar
def test_names_are_similar_exact_match(analyzer):
    assert analyzer._names_are_similar("Alice Smith", "Alice Smith") is True

def test_names_are_similar_middle_initial(analyzer):
    assert analyzer._names_are_similar("Alice Smith", "Alice J Smith") is True

def test_names_are_similar_different_people(analyzer):
    assert analyzer._names_are_similar("Alice Smith", "Bob Jones") is False

def test_names_are_similar_case_insensitive(analyzer):
    assert analyzer._names_are_similar("alice smith", "Alice Smith") is True

def test_names_are_similar_single_shared_word(analyzer):
    """One shared word should not be enough to match"""
    assert analyzer._names_are_similar("Alice Smith", "Bob Smith") is False

def test_names_are_similar_username_style(analyzer):
    """Short single-word usernames only share 1 word — should not match via this method"""
    assert analyzer._names_are_similar("bobdev", "bobdev") is False

# Tests for _load_mailmap
def test_load_mailmap_no_file(analyzer, tmp_path):
    result = analyzer._load_mailmap(str(tmp_path))
    assert result == {}

def test_load_mailmap_parses_entries(analyzer, tmp_path):
    mailmap = tmp_path / ".mailmap"
    mailmap.write_text("Alice Smith <alice@example.com> <alice@users.noreply.github.com>\n")
    result = analyzer._load_mailmap(str(tmp_path))
    assert result == {"alice@users.noreply.github.com": "alice@example.com"}

def test_load_mailmap_ignores_comments(analyzer, tmp_path):
    mailmap = tmp_path / ".mailmap"
    mailmap.write_text("# Auto-generated\nbob <bob@example.com> <bob@users.noreply.github.com>\n")
    result = analyzer._load_mailmap(str(tmp_path))
    assert len(result) == 1
    assert "bob@users.noreply.github.com" in result

# Tests for detect_and_write_mailmap
def test_detect_and_write_mailmap_no_duplicates(analyzer, tmp_path):
    author_map = {
        "alice@example.com": "Alice",
        "bob@example.com": "Bob"
    }
    result = analyzer.detect_and_write_mailmap(str(tmp_path), author_map)
    assert result == author_map
    assert not (tmp_path / ".mailmap").exists()

def test_detect_and_write_mailmap_same_name_different_emails(analyzer, tmp_path):
    author_map = {
        "bob@example.com": "bob",
        "123+bob@users.noreply.github.com": "bob"
    }
    with patch("builtins.input", return_value="y"):
        result = analyzer.detect_and_write_mailmap(str(tmp_path), author_map)
    assert len(result) == 1
    assert (tmp_path / ".mailmap").exists()

def test_detect_and_write_mailmap_similar_names_noreply(analyzer, tmp_path):
    author_map = {
        "alice@example.com": "Alice Smith",
        "123+alicesmith@users.noreply.github.com": "Alice J Smith"
    }
    with patch("builtins.input", return_value="y"):
        result = analyzer.detect_and_write_mailmap(str(tmp_path), author_map)
    assert len(result) == 1
    assert (tmp_path / ".mailmap").exists()

def test_detect_and_write_mailmap_declined_merge(analyzer, tmp_path):
    author_map = {
        "bob@example.com": "bob",
        "123+bob@users.noreply.github.com": "bob"
    }
    with patch("builtins.input", return_value="n"):
        result = analyzer.detect_and_write_mailmap(str(tmp_path), author_map)
    assert len(result) == 2
    assert not (tmp_path / ".mailmap").exists()

def test_detect_and_write_mailmap_does_not_duplicate_existing_entries(analyzer, tmp_path):
    mailmap = tmp_path / ".mailmap"
    existing = "bob <bob@example.com> <123+bob@users.noreply.github.com>"
    mailmap.write_text(f"# Auto-generated\n{existing}\n")
    author_map = {
        "bob@example.com": "bob",
        "123+bob@users.noreply.github.com": "bob"
    }
    with patch("builtins.input", return_value="y"):
        analyzer.detect_and_write_mailmap(str(tmp_path), author_map)
    content = mailmap.read_text()
    assert content.count(existing) == 1

# Tests for ContributionStats
# -------------------------

def test_contribution_stats_to_dict():
    stats = ContributionStats(
        lines_added=10,
        lines_deleted=5,
        total_commits=3,
        files_touched={"file1.py", "file2.py"},
        contribution_by_type={"code": 15, "test": 5, "docs": 0, "other": 0},  # ✅ include other to match model
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
    assert stats.contribution_by_type == {"code": 0, "docs": 0, "test": 0, "other": 0}


def test_calculate_share_returns_dict(analyzer):
    selected_stats = ContributionStats(lines_added=50, lines_deleted=10)
    total_stats = ContributionStats(lines_added=100, lines_deleted=20)
    share = analyzer.calculate_share(selected_stats, total_stats)
    assert isinstance(share, dict)
    assert "contribution_share_percent" in share
    assert share["contribution_share_percent"] == 50.0

def test_get_all_authors_normalizes_and_uses_committer(analyzer):
    commits = [
        create_mock_commit(" Alice   Smith ", {}, author_email="alice@example.com"),
        create_mock_commit("", {}, author_email="carol@example.com", committer_name="  Carol  ", committer_email="carol@example.com"),
        create_mock_commit("", {}, author_email="dave@example.com", committer_name="", committer_email=""),
    ]

    with patch("src.analyzers.contribution_analyzer.Repo") as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.iter_commits.return_value = commits
        result = analyzer.get_all_authors("/fake/path")

    assert result == ["Alice Smith", "Carol", "dave"]
