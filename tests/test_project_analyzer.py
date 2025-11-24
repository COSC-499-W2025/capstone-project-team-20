from unittest.mock import patch, MagicMock
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.Project import Project
from pathlib import Path
import shutil

def test_clean_path_strips_outer_double_quotes():
    analyzer = ProjectAnalyzer()
    result = analyzer.clean_path('"/path/to/file.zip"')
    assert str(result) == "/path/to/file.zip"

def test_clean_path_strips_outer_single_quotes():
    analyzer = ProjectAnalyzer()
    result = analyzer.clean_path("'/path/to/file.zip'")
    assert str(result) == "/path/to/file.zip"

def test_clean_path_preserves_inner_quotes():
    analyzer = ProjectAnalyzer()
    result = analyzer.clean_path("/path/to/dylan's.zip")
    assert str(result).endswith("dylan's.zip")

def test_clean_path_unescapes_shell_characters():
    analyzer = ProjectAnalyzer()
    result = analyzer.clean_path(r"/path/to/my\ file.zip")
    assert "my file.zip" in str(result)

def test_clean_path_unescapes_special_characters():
    analyzer = ProjectAnalyzer()
    result = analyzer.clean_path(r"/path/to/file\&name\(1\).zip")
    assert "file&name(1).zip" in str(result)

def test_clean_path_strips_whitespace():
    analyzer = ProjectAnalyzer()
    result = analyzer.clean_path("  /path/to/file.zip  ")
    assert str(result) == "/path/to/file.zip"

def test_clean_path_expands_tilde():
    analyzer = ProjectAnalyzer()
    with patch("os.path.expanduser", return_value="/Users/dylan/file.zip"):
        result = analyzer.clean_path("~/file.zip")
    assert str(result) == "/Users/dylan/file.zip"

def test_clean_path_handles_complex_escaped_path():
    analyzer = ProjectAnalyzer()
    result = analyzer.clean_path(r"/path/term\ 1\ 2025\:26/dylan\'s.zip")
    assert "term 1 2025:26" in str(result)
    assert "dylan's.zip" in str(result)

def test_load_zip_success():
    analyzer = ProjectAnalyzer()
    fake_root = MagicMock()
    with patch("os.path.exists", return_value=True):
        with patch("zipfile.is_zipfile", return_value=True):
            with patch("src.analyzers.ProjectAnalyzer.parse", return_value=fake_root):
                with patch("builtins.input", side_effect=["/path/fake.zip"]):
                    result = analyzer.load_zip()
    assert result is True
    assert analyzer.root_folder is fake_root

def test_load_zip_retry_then_success():
    analyzer = ProjectAnalyzer()
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



def test_load_zip_parse_error():
    analyzer = ProjectAnalyzer()
    with patch("os.path.exists", return_value=True):
        with patch("zipfile.is_zipfile", return_value=True):
            with patch("builtins.input", return_value="/path/project.zip"):
                with patch("src.analyzers.ProjectAnalyzer.parse", side_effect=Exception("bad zip")):
                    assert analyzer.load_zip() is False


def test_analyze_git_calls_run_analysis_from_path():
    """Test that analyze_git extracts zip, analyzes it, and cleans up temp dir"""
    analyzer = ProjectAnalyzer()
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



def test_analyze_metadata_calls_metadata_extractor():
    analyzer = ProjectAnalyzer()
    analyzer.metadata_extractor = MagicMock()
    analyzer.analyze_metadata()
    analyzer.metadata_extractor.extract_metadata.assert_called_once()

def test_analyze_categories_calls_file_categorizer():
    analyzer = ProjectAnalyzer()
    analyzer.metadata_extractor = MagicMock()
    analyzer.file_categorizer = MagicMock()
    fake_file = MagicMock()
    fake_file.file_name = "a.py"
    analyzer.metadata_extractor.collect_all_files.return_value = [fake_file]
    analyzer.analyze_categories()
    analyzer.file_categorizer.compute_metrics.assert_called_once()

def test_print_tree_calls_toString(capsys):
    analyzer = ProjectAnalyzer()
    analyzer.root_folder = MagicMock()
    with patch("src.analyzers.ProjectAnalyzer.toString", return_value="TREE_OUTPUT"):
        analyzer.print_tree()
    captured = capsys.readouterr()
    assert "TREE_OUTPUT" in captured.out

def test_analyze_languages_filters_unknown(capsys):
    analyzer = ProjectAnalyzer()
    fake_file = MagicMock()
    fake_file.file_name = "a.py"
    analyzer.metadata_extractor = MagicMock()
    analyzer.metadata_extractor.collect_all_files.return_value = [fake_file]
    with patch("src.analyzers.language_detector.detect_language_per_file", return_value="Python"):
        analyzer.analyze_languages()
    out = capsys.readouterr().out
    assert "Python" in out

def test_run_all_calls_methods():
    analyzer = ProjectAnalyzer()
    analyzer.analyze_git = MagicMock()
    analyzer.analyze_metadata = MagicMock()
    analyzer.analyze_categories = MagicMock()
    analyzer.print_tree = MagicMock()
    analyzer.analyze_languages = MagicMock()
    analyzer.run_all()
    analyzer.analyze_git.assert_called_once()
    analyzer.analyze_metadata.assert_called_once()
    analyzer.analyze_categories.assert_called_once()
    analyzer.print_tree.assert_called_once()
    analyzer.analyze_languages.assert_called_once()

def test_display_analysis_results_prints_projects(capsys):
    analyzer = ProjectAnalyzer()
    proj1 = Project(name="Proj1", authors=["Alice"], author_count=1, collaboration_status="COLLABORATIVE")
    proj2 = Project(name="Proj2", authors=["Bob"], author_count=1, collaboration_status="INDIVIDUAL")
    analyzer.display_analysis_results([proj1, proj2])
    out = capsys.readouterr().out
    assert "Proj1" in out
    assert "Proj2" in out
    assert "Alice" in out
    assert "Bob" in out

def test_display_analysis_results_empty(capsys):
    analyzer = ProjectAnalyzer()
    analyzer.display_analysis_results([])
    out = capsys.readouterr().out
    assert "No analysis results to display" in out

