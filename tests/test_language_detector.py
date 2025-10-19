import pytest
from src.language_detector import detect_language

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
        (["README.md"], "Unknown"),
        (["Makefile"], "Unknown"),
        ([""], "Unknown"),
    ]
)

def test_detect_language(setup_fake_project, files, expected_language):
    """Test language detection based on file extensions."""
    project = setup_fake_project(files)
    assert detect_language(project) == expected_language
