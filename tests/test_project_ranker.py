import pytest
from datetime import datetime, timedelta
from src.models.Project import Project
from src.ProjectRanker import ProjectRanker

@pytest.fixture
def base_project():
    """A baseline project fixture for testing."""
    return Project(
        name="TestProject",
        total_loc=5000,
        collaboration_status="collaborative",
        last_modified=datetime.now(),
        test_file_ratio=0.20,
        comment_ratio=0.15,
        testing_discipline_score=0.8,
        documentation_habits_score=0.7,
        modularity_score=0.6,
        language_depth_score=0.9
    )

def test_ranker_calculates_score_for_good_project(base_project):
    """
    Tests that a well-rounded project gets a reasonable score.
    """
    ranker = ProjectRanker(base_project)

    score = ranker.calculate_resume_score()

    # Base score = (0.8*10 + 0.7*10 + 0.6*10 + 0.9*10) = 8+7+6+9 = 30
    # LOC score = log10(5000)*5 ~= 3.7*5 = 18.5
    # Collaboration = 10
    # Recency (recent) ~= 10
    # Best practices (both ratios are ideal) = 5 + 5 = 10
    # Total expected score ~= 30 + 18.5 + 10 + 10 + 10 = 78.5
    assert score == pytest.approx(78.5, abs=1)
    assert base_project.resume_score == score

def test_ranker_handles_poor_project(base_project):
    """
    Tests that a project with poor metrics receives a low score.
    """
    base_project.testing_discipline_score = 0.1
    base_project.documentation_habits_score = 0.1
    base_project.modularity_score = 0.2
    base_project.language_depth_score = 0.3
    base_project.total_loc = 150
    base_project.collaboration_status = "individual"
    base_project.last_modified = datetime.now() - timedelta(days=3 * 365) # 3 years old
    base_project.test_file_ratio = 0.05
    base_project.comment_ratio = 0.02
    ranker = ProjectRanker(base_project)

    score = ranker.calculate_resume_score()

    # Quality = (0.1+0.1+0.2+0.3)*10 = 7
    # LOC ~= log10(150)*5 = 10.8
    # Collaboration = 0
    # Recency (old) ~= 0
    # Ratios (not ideal) = 0
    # Total expected score ~= 7 + 10.8 = 17.8
    assert score == pytest.approx(17.8, abs=1)

def test_ranker_handles_edge_cases(base_project):
    """
    Tests edge cases like zero LOC and no modification date.
    """
    base_project.total_loc = 50  # Below threshold
    base_project.last_modified = None
    ranker = ProjectRanker(base_project)

    score = ranker.calculate_resume_score()

    # LOC score should be 0, recency score should be 0.
    # Expected = 30 (quality) + 0 (LOC) + 10 (collab) + 0 (recency) + 10 (ratios) = 50
    assert score == pytest.approx(50, abs=1)
