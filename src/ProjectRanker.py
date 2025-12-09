import math
from src.models.Project import Project
import json

class ProjectRanker:
    """
    Analyzes a Project object to calculate a 'resume score' indicating its
    value from a recruiter's perspective.
    """
    def __init__(self, project: Project):
        self.project = project

    def calculate_resume_score(self) -> float:
        """
        Calculates a score based on various project metrics.

        The scoring is based on:
        - Code quality dimensions (testing, documentation, modularity).
        - Project scale (lines of code).
        - Collaboration status.
        - Recency of contributions.

        Returns:
            A final score for the project. The score is normalized to a
            reasonable range, but is not strictly capped. Higher is better.
        """
        score = 0.0
        project = self.project

        # 1. Code Quality Dimensions (Max: 40 points)
        # These are the most important signals of software engineering maturity.
        score += project.testing_discipline_score * 10
        score += project.documentation_habits_score * 10
        score += project.modularity_score * 10
        score += project.language_depth_score * 10

        # 2. Project Scale & Complexity (Max: ~20 points)
        # We use a logarithmic scale to reward larger projects without letting
        # massive projects dominate the score unfairly.
        # log10(100) = 2, log10(1000) = 3, log10(10000) = 4, etc.
        if project.total_loc > 100:  # Ignore trivial projects
            score += math.log10(project.total_loc) * 5

        # 3. Collaboration (10 points)
        # Working in a team is a highly valued skill.
        if project.collaboration_status == "collaborative":
            score += 10

        # 4. Recency (Max: 10 points)
        # More recent projects are more relevant.
        if project.last_modified:
            from datetime import datetime, timezone
            days_since_modified = (datetime.now(timezone.utc) - project.last_modified.replace(tzinfo=timezone.utc)).days
            # Score decays over 3 years.
            recency_score = max(0, 10 - (days_since_modified / 109.5)) # 10 points / (3 * 365 / 10)
            score += recency_score

        # 5. Best Practices (Max: 10 points)
        # Good ratios for tests and comments are a plus.
        # Ideal test ratio: 15-30%. Score is highest in this range.
        if 0.15 <= project.test_file_ratio <= 0.30:
            score += 5
        # Ideal comment ratio: 10-20%.
        if 0.10 <= project.comment_ratio <= 0.20:
            score += 5

        self.project.resume_score = score
        print(f"ProjectRanker: Final calculated score = {score:.2f}")

        return score
