from pathlib import Path
import sys

import pytest

# Ensure src/ is on sys.path (same pattern as your other tests)
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from src.analyzers.SkillAnalyzer import SkillAnalyzer  # type: ignore
from src.analyzers.skill_models import SkillProfileItem  # type: ignore


def _write_file(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def test_analyze_basic_project_structure(tmp_path: Path) -> None:
    """
    Smoke test: running SkillAnalyzer on a trivial project should
    return the expected top-level keys and types, including tech_profile.
    """
    # Arrange: tiny Python project with one file and one test
    src_file = tmp_path / "src" / "main.py"
    test_file = tmp_path / "tests" / "test_main.py"

    _write_file(
        src_file,
        "def add(a, b):\n"
        "    # simple function\n"
        "    return a + b\n",
    )
    _write_file(
        test_file,
        "from src.main import add\n"
        "def test_add():\n"
        "    assert add(1, 2) == 3\n",
    )

    analyzer = SkillAnalyzer(tmp_path)

    # Act
    result = analyzer.analyze()

    # Assert: high-level shape
    assert isinstance(result, dict)
    for key in ("skills", "stats", "dimensions", "resume_suggestions"):
        assert key in result

    skills = result["skills"]
    stats = result["stats"]
    dimensions = result["dimensions"]
    resume_suggestions = result["resume_suggestions"]

    # skills: list of SkillProfileItem
    assert isinstance(skills, list)
    assert all(isinstance(s, SkillProfileItem) for s in skills)

    # stats: must contain "overall" and "per_language"
    assert isinstance(stats, dict)
    assert "overall" in stats
    assert "per_language" in stats
    assert isinstance(stats["overall"], dict)
    assert isinstance(stats["per_language"], dict)

    # dimensions: should have each dimension with level/score/raw
    assert isinstance(dimensions, dict)
    for dim_name in ("testing_discipline", "documentation_habits", "modularity", "language_depth"):
        assert dim_name in dimensions
        dim = dimensions[dim_name]
        assert isinstance(dim, dict)
        assert "score" in dim
        assert "level" in dim
        assert "raw" in dim

        score = dim["score"]
        level = dim["level"]
        assert 0.0 <= score <= 1.0
        assert isinstance(level, str)

    # resume_suggestions exists and is a list (currently allowed to be empty)
    assert isinstance(resume_suggestions, list)

    # tech_profile block should exist
    assert "tech_profile" in result
    tech_profile = result["tech_profile"]
    assert isinstance(tech_profile, dict)


def test_tech_profile_has_expected_keys_and_types(tmp_path: Path) -> None:
    """
    tech_profile should always include the agreed-upon keys with sane
    default types, even for a very bare project.
    """
    # Bare minimum project: empty README only
    readme = tmp_path / "README.md"
    _write_file(readme, "# Empty project\n")

    analyzer = SkillAnalyzer(tmp_path)
    result = analyzer.analyze()
    tech = result["tech_profile"]

    # Lists
    for list_key in ("frameworks", "dependencies_list", "dependency_files_list", "build_tools", "readme_keywords"):
        assert list_key in tech
        assert isinstance(tech[list_key], list)
        assert all(isinstance(x, str) for x in tech[list_key])

    # Booleans
    for bool_key in ("has_dockerfile", "has_database", "has_frontend", "has_backend", "has_test_files", "has_readme"):
        assert bool_key in tech
        assert isinstance(tech[bool_key], bool)


def test_tech_profile_detects_readme_and_tests(tmp_path: Path) -> None:
    """
    If a README and test files exist, tech_profile should reflect that.
    """
    # README with some common keywords
    readme = tmp_path / "README.md"
    _write_file(
        readme,
        "# Project\n\n"
        "Installation\n"
        "Usage\n"
        "Testing\n",
    )

    # One test file
    test_file = tmp_path / "tests" / "test_something.py"
    _write_file(
        test_file,
        "def test_dummy():\n"
        "    assert True\n",
    )

    analyzer = SkillAnalyzer(tmp_path)
    result = analyzer.analyze()
    tech = result["tech_profile"]

    assert tech["has_readme"] is True
    assert tech["has_test_files"] is True

    # We don't assert exact keywords, but at least ensure it's a non-empty list
    assert isinstance(tech["readme_keywords"], list)
    assert len(tech["readme_keywords"]) >= 1


def test_tech_profile_detects_dockerfile(tmp_path: Path) -> None:
    """
    Presence of a Dockerfile at project root should set has_dockerfile True.
    """
    dockerfile = tmp_path / "Dockerfile"
    _write_file(
        dockerfile,
        "FROM python:3.11-slim\n"
        "WORKDIR /app\n"
        "CMD ['python', 'main.py']\n",
    )

    analyzer = SkillAnalyzer(tmp_path)
    result = analyzer.analyze()
    tech = result["tech_profile"]

    assert tech["has_dockerfile"] is True
