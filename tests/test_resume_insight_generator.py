import datetime
import random
from unittest.mock import patch, MagicMock

from src.generators.ResumeInsightsGenerator import ResumeInsightsGenerator


class DummyProject:
    """Simple stand-in for Project objects."""
    def __init__(self, authors=None, author_count=None, name="TestProject"):
        self.authors = authors or []
        # author_count is sometimes set manually in ProjectAnalyzer
        self.author_count = author_count if author_count is not None else len(self.authors)
        self.name = name


def make_generator(
    code=10, docs=2, tests=3, config=1, other=1,
    languages=("Java", 60.0),  # language_share
    authors=["A", "B"],        # team of 2
    start="2025-01-01", end="2025-03-01"
):
    metadata = {
        "start_date": datetime.datetime.strptime(start, "%Y-%m-%d"),
        "end_date": datetime.datetime.strptime(end, "%Y-%m-%d"),
    }

    categorized_files = {
        "code": code,
        "docs": docs,
        "test": tests,
        "config": config,
        "other": other,
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
    with patch("random.choice", side_effect=["Engineered", "improving project clarity"]):
        bullets = gen.generate_resume_bullet_points()
    assert "Engineered core features using Java" in bullets[0]
    assert "10+ well-structured source files" in bullets[0]
    assert "Produced 2+ documentation files and implemented 3 automated tests" in "\n".join(bullets)
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
    gen = make_generator(code=10, docs=5, tests=2, config=1, other=2)
    summary = gen.generate_project_summary()
    assert "over 20 files" in summary
    assert "tech stack of Java" in summary
    assert "10 source modules" in summary
    assert "2 automated tests" in summary
    assert "5 documentation files" in summary


def test_tech_stack_output():
    gen = make_generator(languages=("JavaScript", 80.0))
    tech = gen.generate_tech_stack()
    assert tech == "Tech Stack: JavaScript"


def test_portfolio_entry_team_contributor():
    gen = make_generator(code=15, docs=5, tests=5, config=2, languages=("Python", 100.0))
    portfolio = gen.generate_portfolio_entry()
    assert "### TestProject" in portfolio
    assert "**Technologies:** Python" in portfolio
    assert "Team Contributor" in portfolio
    assert "**Key Technical Achievements:**" in portfolio


def test_portfolio_entry_solo_developer():
    gen = make_generator(authors=["Solo"], languages=("Go", 100.0))
    # Force author_count=1 to simulate true solo
    gen.project.author_count = 1
    portfolio = gen.generate_portfolio_entry()
    assert "Solo Developer" in portfolio
    assert "**Technologies:** Go" in portfolio


def test_portfolio_role_uses_author_count_over_selected_usernames():
    # Selected usernames list has length 1, but total repo authors is higher
    gen = make_generator(authors=["me"], languages=("Rust", 100.0))
    gen.project.name = "TeamRepo"
    gen.project.author_count = 3  # total repo authors
    portfolio = gen.generate_portfolio_entry()
    assert "Team Contributor (Team of 3)" in portfolio
    assert "collaborated with 2 other developers" in portfolio
