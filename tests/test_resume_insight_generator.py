import datetime
import random
from unittest.mock import patch

from src.generators.ResumeInsightsGenerator import ResumeInsightsGenerator


class DummyProject:
    """Simple stand-in for Project objects."""
    def __init__(self, authors=None, author_count=None):
        self.authors = authors or []
        # author_count is sometimes set manually in ProjectAnalyzer
        self.author_count = author_count if author_count is not None else len(self.authors)


def make_generator(
    code=10, docs=2, tests=3, config=1,
    languages=("Java", 60.0),  # language_share
    authors=["A", "B"],        # team of 2
    start="2025-01-01", end="2025-03-01"
):
    metadata = {
        "start_date": datetime.datetime.strptime(start, "%Y-%m-%d"),
        "end_date": datetime.datetime.strptime(end, "%Y-%m-%d"),
    }

    categorized_files = {
        "counts": {
            "code": code,
            "docs": docs,
            "test": tests,
            "config": config,
        }
    }

    language_share = {languages[0]: languages[1]}
    language_list = [languages[0]]

    project = DummyProject(authors)

    return ResumeInsightsGenerator(
        metadata=metadata,
        categorized_files=categorized_files,
        language_share=language_share,
        project=project,
        language_list=language_list,
    )


# ---------------------------------------------------------------------
# TESTS
# ---------------------------------------------------------------------

def test_get_category_counts():
    gen = make_generator(code=5, docs=1, tests=2, config=3)
    code, docs, tests, config = gen.get_category_counts()

    assert code == 5
    assert docs == 1
    assert tests == 2
    assert config == 3


def test_bullet_points_basic():
    gen = make_generator()

    # Control randomness
    with patch("random.choice", side_effect=["Engineered", "improving project clarity"]):
        bullets = gen.generate_resume_bullet_points()

    # bullet 1
    assert "Engineered core features using Java" in bullets[0]

    # bullet 2
    assert "Produced 2+ documentation files and implemented 3 automated tests" in bullets[1]

    # team bullet
    assert "Collaborated with a team of 2 developers" in "\n".join(bullets)


def test_bullet_points_solo_project():
    gen = make_generator(authors=["A"], languages=("Python", 100.0))

    with patch("random.choice", return_value="Developed"):
        bullets = gen.generate_resume_bullet_points()

    assert "Independently designed, implemented, and tested" in "\n".join(bullets)


def test_duration_calculation():
    gen = make_generator(start="2025-01-01", end="2025-02-01")

    days = gen._compute_days()
    assert days == 31


def test_generate_project_summary():
    gen = make_generator(code=10, docs=5, tests=2, config=0)

    summary = gen.generate_project_summary()

    assert "tech stack of Java" in summary
    assert "10 source modules" in summary
    assert "2 automated tests" in summary
    assert "5 documentation files" in summary


def test_tech_stack_output():
    gen = make_generator(languages=("JavaScript", 80.0))
    tech = gen.generate_tech_stack()
    assert tech == "Tech Stack: JavaScript"

def test_test_files_not_counted_as_code():
    """
    Ensure test files do NOT count toward code totals
    and appear only in the `test` category.
    """
    gen = make_generator(
        code=5,   # real code files
        docs=2,
        tests=7,  # test files
        config=1,
        languages=("Python", 100.0),
        authors=["A"]
    )

    code, docs, tests, config = gen.get_category_counts()

    # Validate category totals
    assert code == 5
    assert tests == 7
    assert docs == 2
    assert config == 1

    # Validate project summary reflects correct test count
    summary = gen.generate_project_summary()

    assert "5 source modules" in summary
    assert "7 automated tests" in summary
    assert "2 documentation files" in summary

    with patch("random.choice", return_value="Built"):
        bullets = gen.generate_resume_bullet_points()

    bullet_text = "\n".join(bullets)

    assert "5" in bullet_text
    assert "7" in bullet_text

    assert "12" not in bullet_text

