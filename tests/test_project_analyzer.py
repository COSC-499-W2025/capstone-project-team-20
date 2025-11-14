from unittest.mock import patch, MagicMock
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer

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

def test_analyze_git_calls_git_analyzer():
    analyzer = ProjectAnalyzer()
    analyzer.zip_path = "some.zip"

    analyzer.git_analyzer = MagicMock()

    analyzer.analyze_git()

    analyzer.git_analyzer.analyze_zip.assert_called_once_with("some.zip")

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

