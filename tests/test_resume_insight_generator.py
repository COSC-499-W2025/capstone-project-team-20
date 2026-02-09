import datetime
import random
from unittest.mock import patch
from src.generators.ResumeInsightsGenerator import ResumeInsightsGenerator

class DummyProject:
    """Simple stand-in for Project objects for testing."""
    def __init__(self, authors=None, author_count=None, name="TestProject"):
        self.authors = authors or []
        self.author_count = author_count if author_count is not None else len(self.authors)
        self.name = name

def make_generator(
    code=10, docs=2, tests=3, config=1,
    languages=("Java", 60.0),
    authors=["A", "B"],
    start="2025-01-01", end="2025-03-01"
):
    metadata = {"start_date": start, "end_date": end}
    categorized_files = {"code": code, "docs": docs, "test": tests, "config": config}
    language_share = {languages[0]: languages[1]}
    language_list = [languages[0]]
    project = DummyProject(authors)
    return ResumeInsightsGenerator(metadata, categorized_files, language_share, project, language_list)

def test_bullet_points_basic():
    gen = make_generator()
    # Mock random.choice to return predictable verbs/phrases
    with patch("random.choice", side_effect=["Engineered", "enhancing maintainability"]):
        bullets = gen.generate_resume_bullet_points()

    assert len(bullets) >= 4
    assert "Engineered core features using Java, contributing to a codebase of 10+ source files." in bullets
    assert "Produced 2+ documentation files and 3 automated tests, enhancing maintainability." in bullets
    assert "Collaborated with a team of 2 developers using Git-based workflows." in bullets

def test_bullet_points_solo_project():
    gen = make_generator(authors=["A"], languages=("Python", 100.0))
    with patch("random.choice", return_value="Developed"):
        bullets = gen.generate_resume_bullet_points()
    assert "Independently designed, implemented, and tested all major components." in bullets

def test_generate_project_summary():
    gen = make_generator(code=10, docs=5, tests=2, config=1)
    summary = gen.generate_project_summary()
    assert "over 18 files" in summary
    assert "A software project built with Java" in summary
    assert "10 source modules" in summary
    assert "2 tests" in summary # "automated tests" was simplified to "tests"
    assert "5 documentation files" in summary
