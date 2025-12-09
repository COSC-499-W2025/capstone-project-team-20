from datetime import datetime
from src.models.ReportProject import ReportProject


class MockProject:
    """Minimal mock of the full Project model."""
    def __init__(
        self,
        name="Test Project",
        resume_score=5.0,
        bullets=None,
        summary="Summary",
        languages=None,
        language_share=None,
        frameworks=None,
        date_created=None,
        last_modified=None,
        collaboration_status="individual",
    ):
        self.name = name
        self.resume_score = resume_score
        self.bullets = bullets or []
        self.summary = summary
        self.languages = languages or []
        self.language_share = language_share or {}
        self.frameworks = frameworks or []
        self.date_created = date_created
        self.last_modified = last_modified
        self.collaboration_status = collaboration_status


def test_from_project_basic():
    p = MockProject(
        name="Alpha",
        resume_score=9.1,
        bullets=["a", "b"],
        languages=["Python"],
        frameworks=["FastAPI"],
        language_share={"Python": 100},
    )

    rp = ReportProject.from_project(p)

    assert rp.project_name == "Alpha"
    assert rp.resume_score == 9.1
    assert rp.bullets == ["a", "b"]
    assert rp.languages == ["Python"]
    assert rp.frameworks == ["FastAPI"]
    assert rp.language_share == {"Python": 100}


def test_from_project_missing_fields():
    """Ensure defensive getattr logic works."""
    p = MockProject()
    del p.languages
    del p.frameworks

    rp = ReportProject.from_project(p)

    assert rp.languages == []
    assert rp.frameworks == []


def test_to_dict_and_from_dict_roundtrip():
    now = datetime.now()
    rp = ReportProject(
        project_name="X",
        resume_score=3.5,
        bullets=["one"],
        summary="test",
        languages=["Python"],
        language_share={"Python": 80},
        frameworks=["Flask"],
        date_created=now,
        last_modified=now,
        collaboration_status="collaborative",
    )

    d = rp.to_dict()
    rp2 = ReportProject.from_dict(d)

    assert rp2.project_name == "X"
    assert rp2.resume_score == 3.5
    assert rp2.languages == ["Python"]
    assert rp2.language_share == {"Python": 80}
    assert rp2.date_created == now
    assert rp2.last_modified == now
    assert rp2.collaboration_status == "collaborative"


def test_get_primary_language_with_share():
    rp = ReportProject(
        project_name="Test",
        language_share={"Python": 60, "Go": 40},
    )
    assert rp.get_primary_language() == "Python"


def test_get_primary_language_no_share():
    rp = ReportProject(
        project_name="Test",
        languages=["Rust", "C++"],
        language_share={},
    )
    assert rp.get_primary_language() == "Rust"


def test_get_tech_stack_display():
    rp = ReportProject(
        project_name="Test",
        languages=["Python"],
        frameworks=["Django"],
    )
    assert rp.get_tech_stack_display() == "Python, Django"
