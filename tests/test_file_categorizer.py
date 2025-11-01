import pytest
from src.FileCategorizer import FileCategorizer

@pytest.fixture
def mock_categorizer(monkeypatch):
    """Loads fake yaml so that we dont have to call our real yaml. if using the real yaml, changes to it could cause these tests to fail"""
    fake_langs = {"Python": {"extensions": ["py"]}, "C++": {"extensions": ["cpp"]}}
    fake_markup = {"HTML": {"extensions": ["html"]}}
    fake_categories = {
        "code": {"language_source": "languages"},
        "docs": {"extensions": ["md"], "path_patterns": ["docs/"]},
        "design": {"language_source": "markup_languages"},
        "tests": {"path_patterns": ["test/", "tests/"], "extensions": ["spec.js"]},
    }

    def fake_load_yaml(path):
        return {
            "languages": fake_langs,
            "markup_languages": fake_markup,
            "categories": fake_categories
        }
    # patch load_yaml everywhere in this test run
    monkeypatch.setattr("src.FileCategorizer.load_yaml", fake_load_yaml)
    return FileCategorizer()


def test_classify_python_file_returns_code(mock_categorizer):
    file_info = {"path": "main.py", "language": "Python"}

    category = mock_categorizer.classify_file(file_info)
    assert category == "code"

def test_classify_java_file_returns_code(mock_categorizer):
    file_info = {"path": "main.py", "language": "Java"}

    category = mock_categorizer.classify_file(file_info)
    assert category == "code"

def test_classify_docs_by_path(mock_categorizer):
    file_info = {"path": "project/docs/overview.md", "language": "Markdown"}
    assert mock_categorizer.classify_file(file_info) == "docs"

def test_classify_by_extension(mock_categorizer):
    file_info = {"path": "tests/unit/sample.spec.js", "language": "JavaScript"}
    assert mock_categorizer.classify_file(file_info) == "tests"

def test_classify_file_by_design(mock_categorizer):
    file_info = {"path": "ui/index.html", "language": "HTML"}
    assert mock_categorizer.classify_file(file_info) == "design"

def test_unmatched_file_defaults_to_code(mock_categorizer):
    file_info = {"path": "misc/notes.txt", "language": "Unknown"}
    assert mock_categorizer.classify_file(file_info) == "code"

def test_match_path_patterns_case_insensitive(mock_categorizer):
    assert mock_categorizer._match_path_patterns("TESTS/myfile.py", ["tests"])
    assert not mock_categorizer._match_path_patterns("src/myfile.py", ["tests/"])

def test_build_language_map_creates_reverse_mapping(mock_categorizer):
    lang_map = mock_categorizer._build_language_map({"Python": {"extensions": ["py", "pyw"]}})
    assert lang_map["py"] == "Python"
    assert lang_map["pyw"] == "Python"

def test_expand_category_sources_merges_languages(mock_categorizer):
    cats = {
        "code": {"language_source": "languages"},
        "design": {"language_source": "markup_languages"},
        "all": {"language_source": "all"}
    }
    expanded = mock_categorizer._expand_category_sources(cats)
    assert "Python" in expanded["code"]["languages"]
    assert "HTML" in expanded["design"]["languages"]
    assert "Python" in expanded["all"]["languages"] and "HTML" in expanded["all"]["languages"]

def test_compute_metrics_counts_and_percentages(mock_categorizer):
    files = [
        {"path": "main.py", "language": "Python"},
        {"path": "docs/readme.md", "language": "Markdown"},
        {"path": "index.html", "language": "HTML"},
        {"path": "tests/test_main.spec.js", "language": "JavaScript"},
    ]
    metrics = mock_categorizer.compute_metrics(files)

    counts = metrics["counts"]
    percentages = metrics["percentages"]

    assert set(counts.keys()) == {"code", "docs", "design", "tests"}
    assert sum(percentages.values()) == pytest.approx(100.0, rel=1e-2)
