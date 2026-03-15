from src.generators.PortfolioGenerator import PortfolioGenerator


class FakeProject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def test_portfolio_generator_team_role_without_synthetic_contributors():
    project = FakeProject(
        name="CollabProject",
        author_count=3,
        authors=[],
        contributor_roles={},
        author_contributions=[],
        collaboration_status="collaborative",
        test_file_ratio=0.2,
        documentation_habits_score=80,
        total_loc=6000,
    )

    gen = PortfolioGenerator(
        metadata={"start_date": "2025-01-01", "end_date": "2025-03-01"},
        categorized_files={"code": 10, "docs": 2, "test": 3},
        language_share={"Python": 100.0},
        project=project,
        language_list=["Python"],
    )

    details = gen.generate_portfolio_details()
    assert details.project_name == "CollabProject"
    assert details.role.startswith("Team Contributor")
    assert details.contributor_roles == []
    assert "100.0% contribution share" not in details.overview
    assert "/100" not in details.overview
