from unittest.mock import patch, MagicMock, Mock
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.ConfigManager import ConfigManager
from src.Project import Project
from pathlib import Path
import pytest

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
        with patch("src.analyzers.ProjectAnalyzer.parse", return_value=fake_root):
            with patch("builtins.input", side_effect=["/path/fake.zip"]):
                result = analyzer.load_zip()
    assert result is True
    assert analyzer.root_folder is fake_root

def test_load_zip_retry_then_success(analyzer):
    fake_root = MagicMock()
    with patch("os.path.exists", side_effect=[False, True]):
        with patch("builtins.input", side_effect=["bad.zip", "good.zip"]):
            with patch("src.analyzers.ProjectAnalyzer.parse", return_value=fake_root):
                assert analyzer.load_zip() is True
                assert analyzer.root_folder is fake_root

def test_load_zip_parse_error(analyzer):
    with patch("os.path.exists", return_value=True):
        with patch("builtins.input", return_value="project.zip"):
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

# Existing tests updated for new constructor
def test_analyze_metadata_calls_metadata_extractor(analyzer):
    analyzer.metadata_extractor = MagicMock()
    analyzer.analyze_metadata()
    analyzer.metadata_extractor.extract_metadata.assert_called_once()

def test_analyze_categories_calls_file_categorizer(analyzer):
    analyzer.metadata_extractor = MagicMock()
    analyzer.file_categorizer = MagicMock()
    fake_file = MagicMock()
    fake_file.file_name = "a.py"
    analyzer.metadata_extractor.collect_all_files.return_value = [fake_file]
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
    with patch("src.analyzers.language_detector.detect_language_per_file", return_value="Python"):
        analyzer.analyze_languages()
    out = capsys.readouterr().out
    assert "Python" in out
