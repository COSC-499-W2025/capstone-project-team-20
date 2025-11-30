from unittest.mock import patch, MagicMock, Mock
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.ConfigManager import ConfigManager
from src.Project import Project
from pathlib import Path
import shutil
from src.analyzers.ContributionAnalyzer import ContributionStats
import pytest

# Fixtures
@pytest.fixture
def mock_config_manager():
    """Create a mock ConfigManager for testing"""
    mock_cm = MagicMock(spec=ConfigManager)
    mock_cm.get.return_value = None
    return mock_cm

@pytest.fixture
def analyzer(mock_config_manager):
    """Create a ProjectAnalyzer with mocked dependencies"""
    return ProjectAnalyzer(config_manager=mock_config_manager)

def test_init_with_config_manager(mock_config_manager):
    """Test ProjectAnalyzer initializes with ConfigManager"""
    analyzer = ProjectAnalyzer(config_manager=mock_config_manager)
    assert analyzer._config_manager is mock_config_manager
    assert analyzer.repo_finder is not None

def test_load_zip_success(analyzer):
    fake_root = MagicMock()
    with patch("os.path.exists", return_value=True):
        with patch("zipfile.is_zipfile", return_value=True):
            with patch("src.analyzers.ProjectAnalyzer.parse", return_value=fake_root):
                with patch("builtins.input", side_effect=["/path/fake.zip"]):
                    result = analyzer.load_zip()
    assert result is True
    assert analyzer.root_folder is fake_root

def test_load_zip_retry_then_success(analyzer):
    fake_root = MagicMock()

    inputs = iter(["bad.zip", "good.zip"])

    def check_path(path):
        return str(path).endswith("good.zip")

    with patch("os.path.exists", side_effect=check_path):
        with patch("zipfile.is_zipfile", side_effect=check_path):
            with patch("builtins.input", side_effect=lambda prompt: next(inputs)):
                with patch("src.analyzers.ProjectAnalyzer.parse", return_value=fake_root):
                    result = analyzer.load_zip()

    assert result is True
    assert analyzer.root_folder is fake_root

def test_load_zip_parse_error(analyzer):
    with patch("os.path.exists", return_value=True):
        with patch("zipfile.is_zipfile", return_value=True):
            with patch("builtins.input", return_value="/path/project.zip"):
                with patch("src.analyzers.ProjectAnalyzer.parse", side_effect=Exception("bad zip")):
                    assert analyzer.load_zip() is False

# Tests for username prompting
def test_prompt_for_usernames_single_selection(analyzer):
    authors = ["Alice", "Bob", "Charlie"]
    with patch("builtins.input", return_value="1"):
        result = analyzer._prompt_for_usernames(authors)
    assert result == ["Alice"]

def test_prompt_for_usernames_multiple_selection(analyzer):
    authors = ["Alice", "Bob", "Charlie"]
    with patch("builtins.input", return_value="1, 3"):
        result = analyzer._prompt_for_usernames(authors)
    assert result == ["Alice", "Charlie"]

def test_prompt_for_usernames_quit(analyzer):
    authors = ["Alice", "Bob"]
    with patch("builtins.input", return_value="q"):
        result = analyzer._prompt_for_usernames(authors)
    assert result is None

def test_prompt_for_usernames_invalid_then_valid(analyzer):
    authors = ["Alice", "Bob"]
    with patch("builtins.input", side_effect=["abc", "1"]):
        result = analyzer._prompt_for_usernames(authors)
    assert result == ["Alice"]

def test_prompt_for_usernames_out_of_range_then_valid(analyzer):
    authors = ["Alice", "Bob"]
    with patch("builtins.input", side_effect=["99", "2"]):
        result = analyzer._prompt_for_usernames(authors)
    assert result == ["Bob"]

def test_prompt_for_usernames_empty_author_list(analyzer):
    with patch("builtins.input", return_value="1"):
        result = analyzer._prompt_for_usernames([])
    assert result is None

def test_prompt_for_usernames_keyboard_interrupt(analyzer):
    authors = ["Alice"]
    with patch("builtins.input", side_effect=KeyboardInterrupt):
        result = analyzer._prompt_for_usernames(authors)
    assert result is None

def test_prompt_for_usernames_deduplicates(analyzer):
    """Test that selecting the same author multiple times returns unique list"""
    authors = ["Alice", "Bob"]
    with patch("builtins.input", return_value="1, 1, 2"):
        result = analyzer._prompt_for_usernames(authors)
    assert result == ["Alice", "Bob"]

# Tests for _get_or_select_usernames
def test_get_or_select_usernames_existing_config(analyzer, mock_config_manager):
    mock_config_manager.get.return_value = ["Alice", "Bob"]
    authors = ["Alice", "Bob", "Charlie"]
    result = analyzer._get_or_select_usernames(authors)
    assert result == ["Alice", "Bob"]
    mock_config_manager.set.assert_not_called()

def test_get_or_select_usernames_no_config_prompts_user(analyzer, mock_config_manager):
    mock_config_manager.get.return_value = None
    authors = ["Alice", "Bob"]
    with patch.object(analyzer, '_prompt_for_usernames', return_value=["Alice"]):
        result = analyzer._get_or_select_usernames(authors)
    assert result == ["Alice"]
    mock_config_manager.set.assert_called_once_with("usernames", ["Alice"])

def test_get_or_select_usernames_no_authors(analyzer, mock_config_manager):
    mock_config_manager.get.return_value = None
    result = analyzer._get_or_select_usernames([])
    assert result is None
    mock_config_manager.set.assert_not_called()

def test_get_or_select_usernames_user_quits(analyzer, mock_config_manager):
    mock_config_manager.get.return_value = None
    authors = ["Alice"]
    with patch.object(analyzer, '_prompt_for_usernames', return_value=None):
        result = analyzer._get_or_select_usernames(authors)
    assert result is None
    mock_config_manager.set.assert_not_called()

def test_analyze_metadata_calls_metadata_extractor(analyzer):
    analyzer.metadata_extractor = MagicMock()
    analyzer.metadata_extractor.extract_metadata.return_value = {
        "project_metadata": {
            "total_files": 5,
            "total_size_kb": 100,
            "start_date": "2025-01-01T00:00:00",
            "end_date": "2025-01-02T00:00:00",
        }
    }
    analyzer.project_manager = MagicMock()
    analyzer.zip_path = "fake.zip" 

    analyzer.analyze_metadata()

    analyzer.metadata_extractor.extract_metadata.assert_called_once()


def test_analyze_categories_calls_file_categorizer(analyzer):
    analyzer.metadata_extractor = MagicMock()
    analyzer.file_categorizer = MagicMock()
    analyzer.project_manager = MagicMock()

    analyzer.zip_path = "fake.zip"
    analyzer.root_folder = MagicMock()
    analyzer.root_folder.name = "fakefolder"

    fake_file = MagicMock()
    fake_file.file_name = "a.py"

    analyzer.metadata_extractor.collect_all_files.return_value = [fake_file]
    analyzer.file_categorizer.compute_metrics.return_value = {"dummy": True}

    analyzer.analyze_categories()

    analyzer.file_categorizer.compute_metrics.assert_called_once()

def test_print_tree_calls_toString(analyzer, capsys):
    analyzer.root_folder = MagicMock()
    with patch("src.analyzers.ProjectAnalyzer.toString", return_value="TREE_OUTPUT"):
        analyzer.print_tree()
    captured = capsys.readouterr()
    assert "TREE_OUTPUT" in captured.out

def test_analyze_languages_filters_unknown(analyzer, capsys):
    fake_file = MagicMock()
    fake_file.file_name = "a.py"

    analyzer.metadata_extractor = MagicMock()
    analyzer.metadata_extractor.collect_all_files.return_value = [fake_file]

    # REQUIRED for load_or_create_project()
    analyzer.zip_path = "fake.zip"
    analyzer.root_folder = MagicMock()
    analyzer.root_folder.name = "fakefolder"

    with patch("src.analyzers.language_detector.detect_language_per_file",
               return_value="Python"):
        analyzer.analyze_languages()

    out = capsys.readouterr().out
    assert "Python" in out


# Tests for contribution analysis integration (from PR #209)
def test_aggregate_stats_single_author(analyzer):
    """Test aggregation for a single author"""
    stats_dict = {
        "Alice": ContributionStats(
            lines_added=10,
            lines_deleted=5,
            total_commits=2,
            files_touched={"file1.py", "file2.py"},
            contribution_by_type={"code": 15, "test": 0, "docs": 0}
        )
    }
    result = analyzer._aggregate_stats(stats_dict, ["Alice"])
    assert result.lines_added == 10
    assert result.lines_deleted == 5
    assert result.total_commits == 2
    assert len(result.files_touched) == 2

def test_aggregate_stats_multiple_authors(analyzer):
    """Test aggregation combines multiple authors correctly"""
    stats_dict = {
        "Alice": ContributionStats(
            lines_added=10,
            lines_deleted=2,
            total_commits=2,
            files_touched={"file1.py"},
            contribution_by_type={"code": 12, "test": 0, "docs": 0}
        ),
        "Bob": ContributionStats(
            lines_added=20,
            lines_deleted=5,
            total_commits=3,
            files_touched={"file2.py", "file3.py"},
            contribution_by_type={"code": 20, "test": 5, "docs": 0}
        )
    }
    result = analyzer._aggregate_stats(stats_dict, ["Alice", "Bob"])
    assert result.lines_added == 30
    assert result.lines_deleted == 7
    assert result.total_commits == 5
    assert len(result.files_touched) == 3

def test_aggregate_stats_all_authors(analyzer):
    """Test aggregation without selected_authors aggregates everyone"""
    stats_dict = {
        "Alice": ContributionStats(lines_added=10, lines_deleted=2, total_commits=1),
        "Bob": ContributionStats(lines_added=20, lines_deleted=5, total_commits=2)
    }
    result = analyzer._aggregate_stats(stats_dict)
    assert result.lines_added == 30
    assert result.lines_deleted == 7
    assert result.total_commits == 3

def test_display_contribution_results_output(analyzer, capsys):
    """Test that contribution results are formatted correctly"""
    selected_stats = ContributionStats(
        lines_added=50,
        lines_deleted=10,
        total_commits=5,
        files_touched={"file1.py", "file2.py", "file3.py"},
        contribution_by_type={"code": 40, "test": 15, "docs": 5}
    )
    total_stats = ContributionStats(
        lines_added=100,
        lines_deleted=20,
        total_commits=10
    )
    analyzer._display_contribution_results(selected_stats, total_stats, ["Alice", "Bob"])

    out = capsys.readouterr().out
    assert "Contribution Share for: Alice, Bob" in out
    assert "50.00%" in out
    assert "Total Commits: 5" in out
    assert "Files Touched: 3" in out

def test_display_contribution_results_zero_lines(analyzer, capsys):
    """Test handling when project has zero line changes"""
    selected_stats = ContributionStats()
    total_stats = ContributionStats()
    analyzer._display_contribution_results(selected_stats, total_stats, ["Alice"])

    out = capsys.readouterr().out
    assert "No line changes were found" in out

def test_change_selected_users_workflow(analyzer, mock_config_manager):
    """Test the change selected users workflow"""
    analyzer.zip_path = "test.zip"

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.suffix", new_callable=lambda: property(lambda self: ".zip")):
            with patch("src.analyzers.ProjectAnalyzer.extract_zip", return_value=Path("/tmp/test")):
                with patch("shutil.rmtree"):
                    analyzer.repo_finder.find_repos = MagicMock(return_value=[Path("/tmp/test/repo")])
                    analyzer.contribution_analyzer.get_all_authors = MagicMock(return_value=["Alice", "Bob"])

                    with patch.object(analyzer, '_prompt_for_usernames', return_value=["Bob"]):
                        analyzer.change_selected_users()

                    mock_config_manager.set.assert_called_once_with("usernames", ["Bob"])

# Tests from main branch for batch analysis and run_all
def test_run_all_calls_methods(analyzer):
    # Set a dummy zip_path to avoid TypeError in Path()
    analyzer.zip_path = "dummy.zip"
    # Set a dummy root_folder to ensure analysis methods are called
    analyzer.root_folder = MagicMock()
    # Mock the consolidated git/contribution analysis method
    analyzer.analyze_git_and_contributions = MagicMock()
    analyzer.analyze_metadata = MagicMock()
    analyzer.analyze_categories = MagicMock()
    analyzer.print_tree = MagicMock()
    analyzer.analyze_languages = MagicMock()

    analyzer.run_all()

    analyzer.analyze_git_and_contributions.assert_called_once()
    analyzer.analyze_metadata.assert_called_once()
    analyzer.analyze_categories.assert_called_once()
    analyzer.print_tree.assert_called_once()
    analyzer.analyze_languages.assert_called_once()

def test_display_analysis_results_prints_projects(analyzer, capsys):
    proj1 = Project(name="Proj1", authors=["Alice"], author_count=1, collaboration_status="COLLABORATIVE")
    proj2 = Project(name="Proj2", authors=["Bob"], author_count=1, collaboration_status="INDIVIDUAL")
    analyzer.display_analysis_results([proj1, proj2])
    out = capsys.readouterr().out
    assert "Proj1" in out
    assert "Proj2" in out
    assert "Alice" in out
    assert "Bob" in out

def test_display_analysis_results_empty(analyzer, capsys):
    analyzer.display_analysis_results([])
    out = capsys.readouterr().out
    assert "No analysis results to display" in out


class TestBatchAnalyze:
    def test_exits_early_when_directory_missing(self, analyzer, tmp_path: Path, capsys):
        nonexistent = tmp_path / "nonexistent"
        analyzer.batch_analyze(str(nonexistent))
        captured = capsys.readouterr()
        assert "doesn't exist" in captured.out

    def test_exits_early_when_no_zip_files(self, analyzer, tmp_path: Path, capsys):
        analyzer.batch_analyze(str(tmp_path))
        captured = capsys.readouterr()
        assert "No .zip files found" in captured.out

    @patch.object(ProjectAnalyzer, 'run_all')
    @patch('src.analyzers.ProjectAnalyzer.parse')
    def test_calls_run_all_for_each_zip(self, mock_parse, mock_run_all, analyzer, tmp_path: Path):
        (tmp_path / "repo1.zip").touch()
        (tmp_path / "repo2.zip").touch()
        mock_parse.return_value = MagicMock()
        analyzer.batch_analyze(str(tmp_path))
        assert mock_run_all.call_count == 2

    @patch.object(ProjectAnalyzer, 'run_all')
    @patch('src.analyzers.ProjectAnalyzer.parse')
    def test_sets_zip_path_before_run_all(self, mock_parse, mock_run_all, analyzer, tmp_path: Path):
        zip_file = tmp_path / "test_repo.zip"
        zip_file.touch()
        mock_parse.return_value = MagicMock()

        analyzer.batch_analyze(str(tmp_path))

        # Be tolerant of zip_path being either a str or a Path
        assert Path(analyzer.zip_path) == zip_file

    @patch.object(ProjectAnalyzer, 'run_all')
    @patch('src.analyzers.ProjectAnalyzer.parse')
    def test_increments_analyzed_on_success(self, mock_parse, mock_run_all, analyzer, tmp_path: Path, capsys):
        (tmp_path / "repo1.zip").touch()
        (tmp_path / "repo2.zip").touch()
        mock_parse.return_value = MagicMock()
        analyzer.batch_analyze(str(tmp_path))
        captured = capsys.readouterr()
        assert "Analyzed: 2" in captured.out

    @patch.object(ProjectAnalyzer, 'run_all')
    @patch('src.analyzers.ProjectAnalyzer.parse')
    def test_increments_failed_on_exception(self, mock_parse, mock_run_all, analyzer, tmp_path: Path, capsys):
        (tmp_path / "repo1.zip").touch()
        mock_parse.side_effect = Exception("Parse failed")
        analyzer.batch_analyze(str(tmp_path))
        captured = capsys.readouterr()
        assert "Failed: 1" in captured.out

    @patch.object(ProjectAnalyzer, 'run_all')
    @patch('src.analyzers.ProjectAnalyzer.parse')
    def test_continues_after_single_failure(self, mock_parse, mock_run_all, analyzer, tmp_path: Path, capsys):
        (tmp_path / "repo1.zip").touch()
        (tmp_path / "repo2.zip").touch()
        mock_parse.side_effect = [Exception("First fails"), MagicMock()]
        analyzer.batch_analyze(str(tmp_path))
        captured = capsys.readouterr()
        assert "Analyzed: 1" in captured.out
        assert "Failed: 1" in captured.out
