from unittest.mock import patch, MagicMock
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.Project import Project
from pathlib import Path
import shutil
from src.analyzers.ContributionAnalyzer import ContributionStats
from src.ConfigManager import ConfigManager
import pytest

# Fixtures
@pytest.fixture
def mock_config_manager():
    """Create a mock ConfigManager for testing"""
    mock_cm = MagicMock(spec=ConfigManager)
    mock_cm.get.return_value = None
    return mock_cm

@pytest.fixture
def analyzer_with_config(mock_config_manager):
    """Create a ProjectAnalyzer with mocked ConfigManager"""
    return ProjectAnalyzer(config_manager=mock_config_manager)

def test_load_zip_success(mock_config_manager):
    analyzer = ProjectAnalyzer(config_manager=mock_config_manager)
    fake_root = MagicMock()
    with patch("os.path.exists", return_value=True):
        with patch("src.analyzers.ProjectAnalyzer.parse", return_value=fake_root):
            with patch("builtins.input", side_effect=["/path/fake.zip"]):
                result = analyzer.load_zip()
    assert result is True
    assert analyzer.root_folder is fake_root

def test_load_zip_retry_then_success(mock_config_manager):
    analyzer = ProjectAnalyzer(config_manager=mock_config_manager)
    fake_root = MagicMock()
    with patch("os.path.exists", side_effect=[False, True]):
        with patch("builtins.input", side_effect=["bad.zip", "good.zip"]):
            with patch("src.analyzers.ProjectAnalyzer.parse", return_value=fake_root):
                assert analyzer.load_zip() is True
                assert analyzer.root_folder is fake_root

def test_load_zip_parse_error(mock_config_manager):
    analyzer = ProjectAnalyzer(config_manager=mock_config_manager)
    with patch("os.path.exists", return_value=True):
        with patch("builtins.input", return_value="project.zip"):
            with patch("src.analyzers.ProjectAnalyzer.parse", side_effect=Exception("bad zip")):
                assert analyzer.load_zip() is False

@pytest.mark.skip(reason="Tests old GitRepoAnalyzer workflow - not applicable to PR #2")
def test_analyze_git_calls_run_analysis_from_path(mock_config_manager):
    """Test that analyze_git extracts zip, analyzes it, and cleans up temp dir"""
    analyzer = ProjectAnalyzer(config_manager=mock_config_manager)
    analyzer.zip_path = "some.zip"
    git_mock = MagicMock()
    analyzer.git_analyzer = git_mock

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.suffix", new_callable=lambda: property(lambda self: ".zip")):
            with patch("src.analyzers.ProjectAnalyzer.extract_zip", return_value=Path("/tmp/extracted")) as mock_extract:
                with patch("shutil.rmtree") as mock_rmtree:
                    analyzer.analyze_git()
                    mock_extract.assert_called_once_with("some.zip")
                    git_mock.run_analysis_from_path.assert_called_once()
                    called_arg = git_mock.run_analysis_from_path.call_args[0][0]
                    assert isinstance(called_arg, Path)
                    assert str(called_arg) == "/tmp/extracted" or str(called_arg) == "\\tmp\\extracted"
                    mock_rmtree.assert_called_once_with(Path("/tmp/extracted"))

def test_analyze_metadata_calls_metadata_extractor(mock_config_manager):
    analyzer = ProjectAnalyzer(config_manager=mock_config_manager)
    analyzer.metadata_extractor = MagicMock()
    analyzer.analyze_metadata()
    analyzer.metadata_extractor.extract_metadata.assert_called_once()

def test_analyze_categories_calls_file_categorizer(mock_config_manager):
    analyzer = ProjectAnalyzer(config_manager=mock_config_manager)
    analyzer.metadata_extractor = MagicMock()
    analyzer.file_categorizer = MagicMock()
    fake_file = MagicMock()
    fake_file.file_name = "a.py"
    analyzer.metadata_extractor.collect_all_files.return_value = [fake_file]
    analyzer.analyze_categories()
    analyzer.file_categorizer.compute_metrics.assert_called_once()

def test_print_tree_calls_toString(mock_config_manager, capsys):
    analyzer = ProjectAnalyzer(config_manager=mock_config_manager)
    analyzer.root_folder = MagicMock()
    with patch("src.analyzers.ProjectAnalyzer.toString", return_value="TREE_OUTPUT"):
        analyzer.print_tree()
    captured = capsys.readouterr()
    assert "TREE_OUTPUT" in captured.out

def test_analyze_languages_filters_unknown(mock_config_manager, capsys):
    analyzer = ProjectAnalyzer(config_manager=mock_config_manager)
    fake_file = MagicMock()
    fake_file.file_name = "a.py"
    analyzer.metadata_extractor = MagicMock()
    analyzer.metadata_extractor.collect_all_files.return_value = [fake_file]
    with patch("src.analyzers.language_detector.detect_language_per_file", return_value="Python"):
        analyzer.analyze_languages()
    out = capsys.readouterr().out
    assert "Python" in out

@pytest.mark.skip(reason="Tests old GitRepoAnalyzer workflow - not applicable to PR #2")
def test_run_all_calls_methods(mock_config_manager):
    analyzer = ProjectAnalyzer(config_manager=mock_config_manager)
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

@pytest.mark.skip(reason="Tests old GitRepoAnalyzer workflow - not applicable to PR #2")
def test_display_analysis_results_prints_projects(mock_config_manager, capsys):
    analyzer = ProjectAnalyzer(config_manager=mock_config_manager)
    proj1 = Project(name="Proj1", authors=["Alice"], author_count=1, collaboration_status="COLLABORATIVE")
    proj2 = Project(name="Proj2", authors=["Bob"], author_count=1, collaboration_status="INDIVIDUAL")
    analyzer.display_analysis_results([proj1, proj2])
    out = capsys.readouterr().out
    assert "Proj1" in out
    assert "Proj2" in out
    assert "Alice" in out
    assert "Bob" in out

@pytest.mark.skip(reason="Tests old GitRepoAnalyzer workflow - not applicable to PR #2")
def test_display_analysis_results_empty(mock_config_manager, capsys):
    analyzer = ProjectAnalyzer(config_manager=mock_config_manager)
    analyzer.display_analysis_results([])
    out = capsys.readouterr().out
    assert "No analysis results to display" in out

# New tests for contribution analysis (PR #2)
def test_aggregate_stats_single_author(analyzer_with_config):
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
    result = analyzer_with_config._aggregate_stats(stats_dict, ["Alice"])
    assert result.lines_added == 10
    assert result.lines_deleted == 5
    assert result.total_commits == 2
    assert len(result.files_touched) == 2

def test_aggregate_stats_multiple_authors(analyzer_with_config):
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
    result = analyzer_with_config._aggregate_stats(stats_dict, ["Alice", "Bob"])
    assert result.lines_added == 30
    assert result.lines_deleted == 7
    assert result.total_commits == 5
    assert len(result.files_touched) == 3

def test_aggregate_stats_all_authors(analyzer_with_config):
    """Test aggregation without selected_authors aggregates everyone"""
    stats_dict = {
        "Alice": ContributionStats(lines_added=10, lines_deleted=2, total_commits=1),
        "Bob": ContributionStats(lines_added=20, lines_deleted=5, total_commits=2)
    }
    result = analyzer_with_config._aggregate_stats(stats_dict)
    assert result.lines_added == 30
    assert result.lines_deleted == 7
    assert result.total_commits == 3

def test_display_contribution_results_output(analyzer_with_config, capsys):
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
    analyzer_with_config._display_contribution_results(selected_stats, total_stats, ["Alice", "Bob"])

    out = capsys.readouterr().out
    assert "Contribution Share for: Alice, Bob" in out
    assert "50.00%" in out
    assert "Total Commits: 5" in out
    assert "Files Touched: 3" in out

def test_display_contribution_results_zero_lines(analyzer_with_config, capsys):
    """Test handling when project has zero line changes"""
    selected_stats = ContributionStats()
    total_stats = ContributionStats()
    analyzer_with_config._display_contribution_results(selected_stats, total_stats, ["Alice"])

    out = capsys.readouterr().out
    assert "No line changes were found" in out

def test_change_selected_users_workflow(analyzer_with_config, mock_config_manager):
    """Test the change selected users workflow"""
    analyzer_with_config.zip_path = "test.zip"

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.suffix", new_callable=lambda: property(lambda self: ".zip")):
            with patch("src.analyzers.ProjectAnalyzer.extract_zip", return_value=Path("/tmp/test")):
                with patch("shutil.rmtree"):
                    analyzer_with_config.repo_finder.find_repos = MagicMock(return_value=[Path("/tmp/test/repo")])
                    analyzer_with_config.contribution_analyzer.get_all_authors = MagicMock(return_value=["Alice", "Bob"])

                    with patch.object(analyzer_with_config, '_prompt_for_usernames', return_value=["Bob"]):
                        analyzer_with_config.change_selected_users()

                    mock_config_manager.set.assert_called_once_with("usernames", ["Bob"])
