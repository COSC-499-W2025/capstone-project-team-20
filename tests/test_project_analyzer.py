from unittest.mock import patch, MagicMock
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.Project import Project
from pathlib import Path
import shutil

def test_load_zip_success():
    analyzer = ProjectAnalyzer()
    fake_root = MagicMock()
    with patch("os.path.exists", return_value=True):
        with patch("src.analyzers.ProjectAnalyzer.parse", return_value=fake_root):
            with patch("builtins.input", side_effect=["/path/fake.zip"]):
                result = analyzer.load_zip()
    assert result is True
    assert analyzer.root_folder is fake_root

def test_load_zip_retry_then_success():
    analyzer = ProjectAnalyzer()
    fake_root = MagicMock()
    with patch("os.path.exists", side_effect=[False, True]):
        with patch("builtins.input", side_effect=["bad.zip", "good.zip"]):
            with patch("src.analyzers.ProjectAnalyzer.parse", return_value=fake_root):
                assert analyzer.load_zip() is True
                assert analyzer.root_folder is fake_root

def test_load_zip_parse_error():
    analyzer = ProjectAnalyzer()
    with patch("os.path.exists", return_value=True):
        with patch("builtins.input", return_value="project.zip"):
            with patch("src.analyzers.ProjectAnalyzer.parse", side_effect=Exception("bad zip")):
                assert analyzer.load_zip() is False

def test_analyze_git_calls_run_analysis_from_path():
    analyzer = ProjectAnalyzer()
    analyzer.zip_path = "some.zip"
    analyzer.git_analyzer = MagicMock()
    with patch("src.analyzers.ProjectAnalyzer.extract_zip", return_value=Path("/tmp/extracted")) as mock_extract:
        with patch("shutil.rmtree") as mock_rmtree:
            analyzer.analyze_git()
            analyzer.git_analyzer.run_analysis_from_path.assert_called_once_with(Path("/tmp/extracted"))
            mock_extract.assert_called_once_with("some.zip")
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

