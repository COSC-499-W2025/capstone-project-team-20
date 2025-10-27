import pytest
from pathlib import Path
from src.analyzers.language_detector import *

def test_is_source_file():
    """
    is_source_file returns True for any valid, 
    non-hidden file with extension; False otherwise.
    """
    assert is_source_file(Path("main.py")) is True
    assert is_source_file(Path("analysis.R")) is True
    assert is_source_file(Path("README.md")) is True
    assert is_source_file(Path(".gitignore")) is False
    assert is_source_file(Path("Dockerfile")) is False
    assert is_source_file(Path("")) is False

def test_get_file_extension_normal():
    """Test normal file extensions and case insensitivity."""
    assert get_file_extension(Path("main.py")) == "py"
    assert get_file_extension(Path("index.js")) == "js"
    assert get_file_extension(Path("MAIN.PY")) == "py"
    assert get_file_extension(Path("Index.Js")) == "js"
    assert get_file_extension(Path("analysis.R")) == "r"

def test_get_file_extension_hidden_no_extension():
    """Hidden files and files without extensions return empty string."""
    assert get_file_extension(Path(".gitignore")) == ""
    assert get_file_extension(Path(".env")) == ""
    assert get_file_extension(Path("Dockerfile")) == ""
    assert get_file_extension(Path("")) == ""

def test_get_file_extension_multiple_dots():
    """Test files with multiple dots, the extension is returned."""
    assert get_file_extension(Path("archive.tar.gz")) == "gz"
    assert get_file_extension(Path("my.script.sh")) == "sh"

def test_find_first_valid_extension_empty():
    """Empty file list returns None."""
    assert find_first_valid_extension([]) is None

def test_find_first_valid_extension_no_valid_files():
    """All files are hidden or without extension, return None."""
    files = [".gitignore", "Dockerfile", ".env"]
    assert find_first_valid_extension(files) is None

def test_find_first_valid_extension_single_valid_file():
    """Single valid source file returns its extension."""
    assert find_first_valid_extension(["main.py"]) == "py"
    assert find_first_valid_extension(["analysis.R"]) == "r"

def test_find_first_valid_extension_multiple_files():
    """
    When multiple files are present, the first valid extension is returned.
    Only checks for non-hidden files with extensions, not language support.
    """
    assert find_first_valid_extension([".gitignore", "main.py", "script.rb"]) == "py"
    assert find_first_valid_extension(["Dockerfile", "index.js", "app.ts"]) == "js"
    assert find_first_valid_extension([".env", "Dockerfile", "index.js"]) == "js"
    assert find_first_valid_extension(["README.md", ".gitignore", "script.rb"]) == "md"

class FakeProject:
    """A fake project class to simulate different file types projects include."""
    def __init__(self, files):
        self.files = files

@pytest.fixture
def setup_fake_project():
    """Fixture to create a fake project with given file types."""
    def _setup(files):
        return FakeProject(files=files)
    return _setup

@pytest.mark.parametrize(
    "files, expected_language",
    [
        # Single supported language files
        (["main.py"], "Python"),
        (["app.js"], "JavaScript"),
        (["app.ts"], "TypeScript"),
        (["Program.java"], "Java"),
        (["script.rb"], "Ruby"),
        (["server.go"], "Go"),
        (["Program.cs"], "C#"),
        (["main.c"], "C"),
        (["main.cpp"], "C++"),
        (["index.php"], "PHP"),
        (["lib.rs"], "Rust"),
        (["Main.kt"], "Kotlin"),
        (["script.sh"], "Shell"),
        (["analysis.R"], "R"),
        (["Program.scala"], "Scala"),

        # Unsupported or unknown languages
        (["README.md"], "Unknown"),
        (["Makefile"], "Unknown"),
        ([""], "Unknown"),
        ([".env"], "Unknown"),
        (["Dockerfile"], "Unknown"),
        (["archive.tar.gz"], "Unknown"),

        # Multiple files, first valid determines language
        (["main.py", "app.js"], "Python"),
        (["README.md", "script.rb"], "Unknown"),
        ([".gitignore", "index.php"], "PHP"),
        ([".env", "lib.rs"], "Rust"),
    ]
)

def test_detect_language(setup_fake_project, files, expected_language):
    """Returns correct programming language based on file extensions in the project."""
    project = setup_fake_project(files)
    assert detect_language(project.files, language_map=LANGUAGE_MAP) == expected_language
