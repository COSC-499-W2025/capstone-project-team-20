from pathlib import Path
import sys

import pytest

# Ensure src/ is on sys.path (same pattern as your existing tests)
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from analyzers.code_metrics_analyzer import CodeMetricsAnalyzer, CodeFileAnalysis  # type: ignore


def _write_file(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def test_code_metrics_counts_code_and_test_files(tmp_path: Path):
    """
    Ensure CodeMetricsAnalyzer:
      - picks up both code and test files,
      - correctly flags test files via FileCategorizer.
    """
    # Arrange: create a minimal Python project structure
    src_file = tmp_path / "src" / "main.py"
    test_file = tmp_path / "tests" / "test_main.py"

    _write_file(
        src_file,
        """# main module

def foo():
    return 1
""",
    )

    _write_file(
        test_file,
        """# tests for main

def test_foo():
    assert True
""",
    )

    analyzer = CodeMetricsAnalyzer(tmp_path)

    # Act
    analyses = analyzer.analyze()
    summary = analyzer.summarize(analyses)

    # Assert: we should have two analyzed files
    assert len(analyses) == 2

    # Map by relative path for easier checking
    by_name = {a.path.relative_to(tmp_path).as_posix(): a for a in analyses}
    assert "src/main.py" in by_name
    assert "tests/test_main.py" in by_name

    code_analysis = by_name["src/main.py"]
    test_analysis = by_name["tests/test_main.py"]

    # main.py should be considered non-test
    assert code_analysis.is_test is False
    # tests/test_main.py should be considered a test file
    # NOTE: this assumes your FileCategorizer assigns category "test" for test files
    assert test_analysis.is_test is True

    # Overall summary should reflect 1 code file + 1 test file
    overall = summary["overall"]
    assert overall["total_files"] == 2
    assert overall["num_code_files"] == 1
    assert overall["num_test_files"] == 1
    # Ratio uses code_files as denominator
    assert overall["test_file_ratio"] == pytest.approx(1.0)


def test_code_metrics_comment_and_blank_lines(tmp_path: Path):
    """
    Verify comment_lines, blank_lines, and comment_ratio are computed correctly.
    """
    file_path = tmp_path / "script.py"
    _write_file(
        file_path,
        """
# first comment

x = 1  # inline comment
y = 2

# second comment
""".lstrip(
            "\n"
        ),
    )

    analyzer = CodeMetricsAnalyzer(tmp_path)
    analyses = analyzer.analyze()
    summary = analyzer.summarize(analyses)

    assert len(analyses) == 1
    analysis = analyses[0]

    # total_lines includes all lines (code + blanks + comments)
    assert analysis.total_lines > 0

    # We know there are at least 2 standalone comment lines (starting with "#")
    # and one inline comment (same line as code). The analyzer's heuristic
    # counts the line as comment if it *starts* with "#", so we expect 2.
    assert analysis.comment_lines == 2

    # There should be at least one blank line
    assert analysis.blank_lines >= 1

    # Code lines are the rest (we won't assert the exact number, just that it's > 0)
    assert analysis.code_lines > 0

    overall = summary["overall"]
    # comment_ratio = comment / (comment + code)
    ratio = overall["comment_ratio"]
    assert 0.0 < ratio < 1.0


def test_code_metrics_function_detection(tmp_path: Path):
    """
    Ensure that function_count and max_function_length are detected
    for a simple Python module with multiple functions.
    """
    file_path = tmp_path / "module.py"
    _write_file(
        file_path,
        """
def short():
    return 1


def long_function():
    x = 1
    y = 2
    z = x + y
    return z
""".lstrip(
            "\n"
        ),
    )

    analyzer = CodeMetricsAnalyzer(tmp_path)
    analyses = analyzer.analyze()
    summary = analyzer.summarize(analyses)

    assert len(analyses) == 1
    analysis = analyses[0]

    # We defined exactly two functions
    assert analysis.function_count == 2

    # Largest function length should be > 1
    assert analysis.max_function_length > 1

    overall = summary["overall"]
    # avg_functions_per_file should be close to 2 for this project
    assert overall["avg_functions_per_file"] == pytest.approx(2.0)

def test_ignored_directories_are_pruned(tmp_path: Path):
    """
    Ensure that heavy/ignored directories like node_modules and Unity build/cache
    are not traversed by CodeMetricsAnalyzer and do not appear in analyses.
    """
    # "Real" source file we care about
    src_file = tmp_path / "src" / "main.py"
    _write_file(src_file, "def foo():\n    return 1\n")

    # Noisy dirs that should be ignored
    node_file = tmp_path / "node_modules" / "pkg" / "index.js"
    _write_file(node_file, "console.log('should be ignored');\n")

    unity_cache_file = tmp_path / "Library" / "ScriptAssemblies" / "something.dll"
    _write_file(unity_cache_file, "binary junk")

    analyzer = CodeMetricsAnalyzer(tmp_path)

    analyses = list(analyzer.analyze())
    rel_paths = {a.path.relative_to(tmp_path).as_posix() for a in analyses}

    # main.py should be present
    assert "src/main.py" in rel_paths

    # Files in ignored dirs must NOT be present
    assert not any("node_modules" in p for p in rel_paths)
    assert not any("Library" in p for p in rel_paths)
