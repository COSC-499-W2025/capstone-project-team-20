from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from src.analyzers.SkillAnalyzer import SkillAnalyzer
from src.analyzers.skill_models import SkillProfileItem


def _write_file(path: Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


def test_skill_analyzer_dimensions_and_resume_suggestions(tmp_path: Path):
    """
    Verify that SkillAnalyzer:
      - returns 'dimensions' with the expected feedbackable fields,
      - each dimension has a score in [0, 1] and a valid level,
      - 'resume_suggestions' exists and is a list (currently empty by design).
    """
    # Arrange: small project with code, tests, and comments
    src_file = tmp_path / "src" / "main.py"
    test_file = tmp_path / "tests" / "test_main.py"

    _write_file(
        src_file,
        """
# main module comment

def foo():
    # inner comment
    return 1

def bar():
    return 2
""".lstrip(
            "\n"
        ),
    )

    _write_file(
        test_file,
        """
# tests for main

def test_foo():
    assert foo() == 1
""".lstrip(
            "\n"
        ),
    )

    analyzer = SkillAnalyzer(tmp_path)

    # Act
    result = analyzer.analyze()

    # Basic shape checks
    assert isinstance(result, dict)
    assert "skills" in result
    assert "stats" in result
    assert "dimensions" in result
    assert "resume_suggestions" in result

    skills = result["skills"]
    dimensions = result["dimensions"]
    resume_suggestions = result["resume_suggestions"]

    # Skills should be a list of SkillProfileItem
    assert isinstance(skills, list)
    assert all(isinstance(s, SkillProfileItem) for s in skills)

    # Dimensions block should contain the feedbackable keys
    expected_dims = {
        "testing_discipline",
        "documentation_habits",
        "modularity",
        "language_depth",
    }
    assert expected_dims.issubset(dimensions.keys())

    valid_levels = {"strong", "good", "ok", "needs_improvement"}

    for name in expected_dims:
        dim = dimensions[name]
        assert "score" in dim
        assert "level" in dim
        assert "raw" in dim

        score = dim["score"]
        level = dim["level"]

        # Scores must be normalized to [0, 1]
        assert 0.0 <= score <= 1.0
        # Level should be one of the defined buckets
        assert level in valid_levels
        # raw should be a dict of underlying metrics
        assert isinstance(dim["raw"], dict)

    # Resume suggestions: exists and is a list (currently allowed to be empty)
    assert isinstance(resume_suggestions, list)
