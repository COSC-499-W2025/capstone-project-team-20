import pytest

from src.services.InsightEditor import InsightEditor
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer


SAMPLE_ENTRY = """### COSC310-Team-2
**Role:** Team Contributor (Team of 7) | **Timeline:** 25 days
**Technologies:** Java, JavaScript, SQL, CSS

**Project Overview:**
A software solution collaborated with 6 other developers to build over a 25 days period.

**Key Technical Achievements:**
* Architected a substantial codebase of over 96,890 lines of code.
* Integrated automated tests to support continuous integration.
"""


# ----------------------------
# Parse / Build unit tests
# ----------------------------

def test_parse_portfolio_entry_extracts_fields():
    parts = InsightEditor.parse_portfolio_entry(SAMPLE_ENTRY)

    # Your parser stores the whole first line, including "### "
    assert parts.title == "### COSC310-Team-2"
    assert parts.role_line.strip() == "**Role:** Team Contributor (Team of 7) | **Timeline:** 25 days"
    assert parts.tech_line.strip() == "**Technologies:** Java, JavaScript, SQL, CSS"
    assert parts.overview.strip() == "A software solution collaborated with 6 other developers to build over a 25 days period."
    assert parts.achievements == [
        "Architected a substantial codebase of over 96,890 lines of code.",
        "Integrated automated tests to support continuous integration.",
    ]


def test_build_portfolio_entry_contains_all_sections():
    parts = InsightEditor.parse_portfolio_entry(SAMPLE_ENTRY)
    rebuilt = InsightEditor.build_portfolio_entry(parts)

    assert "### COSC310-Team-2" in rebuilt
    assert "**Project Overview:**" in rebuilt
    assert "**Key Technical Achievements:**" in rebuilt
    assert "* Architected a substantial codebase" in rebuilt
    assert "* Integrated automated tests" in rebuilt


def test_parse_build_round_trip_is_stable():
    parts = InsightEditor.parse_portfolio_entry(SAMPLE_ENTRY)
    rebuilt = InsightEditor.build_portfolio_entry(parts)

    parts2 = InsightEditor.parse_portfolio_entry(rebuilt)

    assert parts2.title == parts.title
    assert parts2.role_line.strip() == parts.role_line.strip()
    assert parts2.tech_line.strip() == parts.tech_line.strip()
    assert parts2.overview.strip() == parts.overview.strip()
    assert parts2.achievements == parts.achievements


def test_build_falls_back_when_no_achievements():
    parts = InsightEditor.parse_portfolio_entry(SAMPLE_ENTRY)
    parts.achievements = []
    rebuilt = InsightEditor.build_portfolio_entry(parts)

    assert "**Key Technical Achievements:**" in rebuilt
    assert "* Delivered a functional codebase using modern development practices." in rebuilt


def test_parse_handles_missing_achievements_section():
    entry = """### ProjectX
**Role:** Solo Developer | **Timeline:** 3 days
**Technologies:** Python

**Project Overview:**
Just an overview.
"""
    parts = InsightEditor.parse_portfolio_entry(entry)

    assert parts.title == "### ProjectX"
    assert parts.role_line.strip() == "**Role:** Solo Developer | **Timeline:** 3 days"
    assert parts.tech_line.strip() == "**Technologies:** Python"
    assert parts.overview.strip() == "Just an overview."
    assert parts.achievements == []


# ----------------------------
# CLI edit tests (monkeypatch input)
# ----------------------------

@pytest.fixture
def analyzer():
    # Create ProjectAnalyzer instance without running __init__ (avoids DB/config deps)
    return ProjectAnalyzer.__new__(ProjectAnalyzer)


CLI_SAMPLE_ENTRY = """### COSC310-Team-2
**Role:** Solo Developer | **Timeline:** 0 days
**Technologies:** Java, JavaScript

**Project Overview:**
Old overview.

**Key Technical Achievements:**
* Old achievement
"""


def test_cli_edit_overview(monkeypatch, analyzer):
    # 3 = overview, then provide new text, then 5 = done
    inputs = iter(["3", "New overview!", "5"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    updated = analyzer.edit_portfolio_entry_cli(CLI_SAMPLE_ENTRY)
    parts = InsightEditor.parse_portfolio_entry(updated)

    assert parts.overview == "New overview!"


def test_cli_edit_role_line(monkeypatch, analyzer):
    inputs = iter(["1", "**Role:** Big Dog | **Timeline:** 16 days", "5"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    updated = analyzer.edit_portfolio_entry_cli(CLI_SAMPLE_ENTRY)
    assert "**Role:** Big Dog | **Timeline:** 16 days" in updated


def test_cli_add_achievement(monkeypatch, analyzer):
    # 4 = achievements menu
    # 'a' add
    # then back (empty input) and done
    inputs = iter([
        "4",
        "a",
        "New achievement",
        "",
        "5",
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    updated = analyzer.edit_portfolio_entry_cli(CLI_SAMPLE_ENTRY)
    parts = InsightEditor.parse_portfolio_entry(updated)

    assert "New achievement" in parts.achievements


def test_cli_delete_achievement(monkeypatch, analyzer):
    # 4 achievements, 'd' delete, '1' delete first, then back, done
    inputs = iter([
        "4",
        "d",
        "1",
        "",
        "5",
    ])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    updated = analyzer.edit_portfolio_entry_cli(CLI_SAMPLE_ENTRY)
    parts = InsightEditor.parse_portfolio_entry(updated)

    assert parts.achievements == ["Delivered a functional codebase using modern development practices."]

