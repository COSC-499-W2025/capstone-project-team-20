import io
import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from pathlib import Path

import src.api.routes as routes
from src.api.api_main import app
from src.managers.ProjectManager import ProjectManager
from src.models.Project import Project
from src.models.Report import Report
from src.models.ReportProject import ReportProject, PortfolioDetails


# Shared Test Client, fake HTTP client connected to FastAPI app.
@pytest.fixture
def client():
    return TestClient(app)


# Fake Project
class FakeProject:
    def __init__(
        self,
        id,
        name,
        skills_used=None,
        categories=None,
        num_files=0,
        test_file_ratio=0.0,
        languages=None,
        language_share=None,
        author_count=1,
        collaboration_status="individual",
        size_kb=0,
        total_loc=0,
        date_created=None,
        last_modified=None,
        contributor_roles=None,
        bullets=None,
        summary="",
        resume_score=0.0,
        portfolio_details=None,
        frameworks=None,
        file_path="fake/path.zip",
        ):
        self.id = id
        self.name = name
        self.skills_used = skills_used or []
        self.contributor_roles = contributor_roles or {}
        self.categories = categories or {}
        self.num_files = num_files
        self.test_file_ratio = test_file_ratio
        self.languages = languages or []
        self.language_share = language_share or {}
        self.author_count = author_count
        self.collaboration_status = collaboration_status
        self.size_kb = size_kb
        self.total_loc = total_loc
        self.date_created = date_created
        self.last_modified = last_modified
        self.bullets = bullets or []
        self.summary = summary
        self.resume_score = resume_score
        self.portfolio_details = portfolio_details
        self.frameworks = frameworks or []
        self.file_path = file_path


def test_privacy_consent_sets_value(client, monkeypatch):
    calls = {}

    class FakeConsentManager:
        def has_user_consented(self):
            return True  # not needed here but safe

        def set_consent(self, consent: bool):
            calls["consent"] = consent

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)

    res = client.post("/privacy-consent", json={"consent": True})
    assert res.status_code == 200

    data = res.json()
    assert data["consent"] is True
    assert calls["consent"] is True

def test_get_privacy_consent_true(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)

    res = client.get("/privacy-consent")
    assert res.status_code == 200
    assert res.json()["consent"] is True


def test_get_privacy_consent_false(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return False

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)

    res = client.get("/privacy-consent")
    assert res.status_code == 200
    assert res.json()["consent"] is False


def test_get_privacy_consent_independent_of_post(client, monkeypatch):
    """GET should reflect whatever ConsentManager returns, not be affected by prior POST state."""
    state = {"consent": False}

    class FakeConsentManager:
        def has_user_consented(self):
            return state["consent"]

        def set_consent(self, value):
            state["consent"] = value

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)

    res = client.get("/privacy-consent")
    assert res.json()["consent"] is False

    client.post("/privacy-consent", json={"consent": True})

    res = client.get("/privacy-consent")
    assert res.json()["consent"] is True


# /projects (list) test. testing GET /project
def test_get_projects_list(client, monkeypatch):
    class FakeProjectManager:
        def get_project_groups(self):
            return {
                "current": [FakeProject(2, "B")],
                "previous": [FakeProject(1, "A")],
            }

    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)

    res = client.get("/projects")
    assert res.status_code == 200

    data = res.json()
    # API concatenates current_projects followed by previous_projects
    assert data["projects"] == [
        {"id": 2, "name": "B"},
        {"id": 1, "name": "A"},
    ]
    assert data["previous_projects"] == [{"id": 1, "name": "A"}]
    assert data["current_projects"] == [{"id": 2, "name": "B"}]

#/projects/{id} test. GET /projects/5 test.
def test_get_project_found(client, monkeypatch):
    class FakeProjectManager:
        def get(self, id: int):
            return FakeProject(id, "CoolProj", skills_used=["Python"], contributor_roles={"alice": {"primary_role": "role_backend"}})

    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)

    res = client.get("/projects/5")
    assert res.status_code == 200

    data = res.json()
    assert data["ok"] is True
    assert data["project"]["id"] == 5
    assert data["project"]["name"] == "CoolProj"
    assert data["project"]["contributor_roles"]["alice"]["primary_role"] == "role_backend"


# Testing ProjectManager.get(id) returns None
def test_get_project_not_found(client, monkeypatch):
    class FakeProjectManager:
        def get(self, id: int):
            return None

    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)

    res = client.get("/projects/999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Project not found."


# testing GET /skills returns 200
def test_skills_counts_and_sorts(client, monkeypatch):
    class FakeProjectManager:
        def get_all(self):
            return [
                FakeProject(1, "P1", skills_used=["Python", "SQL", "Python"]),
                FakeProject(2, "P2", skills_used=["SQL", "C#"]),
                FakeProject(3, "P3", skills_used=[None, "  Python  "]),
            ]

    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)

    res = client.get("/skills")
    assert res.status_code == 200

    data = res.json()
    assert data["ok"] is True
    assert data["skills"] == [
        {"name": "Python", "project_count": 3},
        {"name": "SQL", "project_count": 2},
        {"name": "C#", "project_count": 1},
    ]


# /projects/upload. test of POST /projects/upload returns 201
def test_upload_project_success(client, monkeypatch):
    # fake that zip parser found one root folder
    monkeypatch.setattr(routes, "parse_zip_to_project_folders", lambda _: ["root1"])

    class FakeAnalyzer:
        def __init__(self, config, root_folders, tmp_path):
            self.config = config
            self.root_folders = root_folders
            self.tmp_path = tmp_path
            self.changed_project_names = ["Proj1", "Proj2"]

        def initialize_projects(self):
            return [FakeProject(1, "Proj1"), FakeProject(2, "Proj2")]
        
        def analyze_git_and_contributions(self, projects, interactive=False):
            return []

    monkeypatch.setattr(routes, "ProjectAnalyzer", FakeAnalyzer)

    files = {"zip_file": ("test.zip", io.BytesIO(b"fake zip bytes"), "application/zip")}
    res = client.post("/projects/upload", files=files)

    assert res.status_code == 201

    data = res.json()
    assert data["ok"] is True
    assert data["projects"] == [
        {"id": 1, "name": "Proj1"},
        {"id": 2, "name": "Proj2"},
    ]

def test_upload_project_triggers_analyses(client, monkeypatch):
    monkeypatch.setattr(routes, "parse_zip_to_project_folders", lambda _: ["root1"])

    calls = []

    class FakeAnalyzer:
        def __init__(self, config, root_folders, tmp_path):
            self.config = config
            self.root_folders = root_folders
            self.tmp_path = tmp_path
            self.changed_project_names = ["Proj1"]

        def initialize_projects(self):
            return [FakeProject(1, "Proj1")]

        def analyze_git_and_contributions(self, projects=None, interactive=True):
            calls.append(("git", len(projects or []), interactive))

        def analyze_metadata(self, projects=None):
            calls.append(("metadata", len(projects or [])))

        def analyze_categories(self, projects=None):
            calls.append(("categories", len(projects or [])))

        def analyze_languages(self, projects=None):
            calls.append(("languages", len(projects or [])))

        def analyze_skills(self, projects=None, silent=False):
            calls.append(("skills", len(projects or []), silent))

    monkeypatch.setattr(routes, "ProjectAnalyzer", FakeAnalyzer)

    files = {"zip_file": ("test.zip", io.BytesIO(b"fake zip bytes"), "application/zip")}
    res = client.post("/projects/upload", files=files)

    assert res.status_code == 201
    assert calls == [
        ("git", 1, False),
        ("metadata", 1),
        ("categories", 1),
        ("languages", 1),
        ("skills", 1, True),
    ]


def test_upload_project_invalid_zip_returns_400(client, monkeypatch):
    # Simulate invalid zip (no root folders)
    monkeypatch.setattr(routes, "parse_zip_to_project_folders", lambda _: [])

    files = {"zip_file": ("bad.zip", io.BytesIO(b"bad"), "application/zip")}
    res = client.post("/projects/upload", files=files)

    assert res.status_code == 400
    assert "Zip parsed no projects" in res.json()["detail"]

def test_get_portfolio_report_found(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True
    details = PortfolioDetails(
        project_name="Proj",
        role="Backend Developer",
        timeline="1 month",
        technologies="Python",
        overview="Overview",
        achievements=["A"],
        contributor_roles=[{"name": "alice", "role": "Backend", "confidence": 0.8, "confidence_pct": 80}],
    )
    project = ReportProject(
        project_name="Proj",
        resume_score=2.5,
        portfolio_details=details,
        languages=["Python"],
        language_share={"Python": 100.0},
        frameworks=[],
        date_created=datetime(2025, 1, 1),
        last_modified=datetime(2025, 2, 1),
        collaboration_status="individual",
    )
    report = Report(
        id=1,
        title="Portfolio Report",
        date_created=datetime(2025, 2, 2),
        sort_by="resume_score",
        projects=[project],
        notes=None,
        report_kind="portfolio",
    )

    class FakeReportManager:
        def get_report(self, id: int):
            return report if id == 1 else None

    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)
    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)

    res = client.get("/portfolio/1")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["portfolio"]["id"] == 1
    assert data["portfolio"]["projects"][0]["portfolio_details"]["contributor_roles"][0]["role"] == "Backend"

def test_export_portfolio_success(client, monkeypatch):
    """
    HTTP: POST /portfolio/export
    Exercise portfolio PDF export endpoint with valid input,
    expects HTTP 200 OK and valid download URL in response.
    """
    class FakeConsentManager:
        def has_user_consented(self):
            return True
    report = Report(
        id=2,
        title="My Report",
        date_created=datetime(2025, 1, 1),
        sort_by="resume_score",
        projects=[],
        notes=None,
        report_kind="portfolio",
    )

    class FakeReportManager:
        def get_report(self, id: int):
            return report if id == 2 else None

    calls = {}

    class FakeReportExporter:
        def export_to_pdf(self, report, config_manager, output_path: str, template: str):
            calls["output_path"] = output_path
            calls["template"] = template
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(b"FAKE PDF DATA")

    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)
    monkeypatch.setattr(routes, "ReportExporter", FakeReportExporter)
    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)

    res = client.post("/portfolio/export", json={"report_id": 2, "output_name": "output.pdf"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["download_url"].startswith("/portfolio/exports/")
    assert calls["template"] == "portfolio"
    assert calls["output_path"].startswith("portfolios/")
    assert calls["output_path"].endswith("-output.pdf")

def test_edit_portfolio_updates_report(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True
    report = Report(
        id=3,
        title="Old Title",
        date_created=datetime(2025, 1, 1),
        sort_by="resume_score",
        projects=[],
        notes=None,
        report_kind="portfolio",
    )

    class FakeReportManager:
        def get_report(self, id: int):
            return report if id == 3 else None
        def update_report(self, updated):
            report.title = updated.title
            report.notes = updated.notes
            return True

    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)
    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)

    res = client.post("/portfolio/3/edit", json={"title": "New Title", "notes": "Updated"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["portfolio"]["title"] == "New Title"
    assert data["portfolio"]["notes"] == "Updated"

def test_badge_progress_returns_closest_project(client, monkeypatch):
    class FakeProjectManager:
        def get_all(self):
            return [
                FakeProject(1, "DocsHeavy", categories={"docs": 30, "code": 40}, num_files=100, test_file_ratio=0.05),
                FakeProject(2, "TestsHeavy", categories={"docs": 10, "code": 80}, num_files=100, test_file_ratio=0.2, languages=["Python", "JS", "SQL"]),
            ]

    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)

    res = client.get("/badges/progress")
    assert res.status_code == 200
    data = res.json()

    as_map = {item["badge_id"]: item for item in data["badges"]}
    assert as_map["test_pilot"]["earned"] is True
    assert as_map["test_pilot"]["project"]["name"] == "TestsHeavy"
    assert as_map["docs_guardian"]["project"]["name"] == "DocsHeavy"

def test_badge_progress_uses_fallback_fields(client, monkeypatch):
    class FakeProjectManager:
        def get_all(self):
            return [
                FakeProject(
                    9,
                    "NestedCounts",
                    categories={"counts": {"test": 8, "docs": 12, "code": 35}},
                    num_files=50,
                    language_share={"Python": 70.0, "TypeScript": 20.0, "SQL": 10.0},
                    author_count=0,
                ),
            ]

    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)

    res = client.get("/badges/progress")
    assert res.status_code == 200

    data = res.json()
    as_map = {item["badge_id"]: item for item in data["badges"]}

    assert as_map["test_pilot"]["earned"] is True
    assert as_map["docs_guardian"]["earned"] is True
    assert as_map["code_cruncher"]["earned"] is True
    assert as_map["polyglot"]["earned"] is True
    assert as_map["team_effort"]["project"]["name"] == "NestedCounts"

def test_yearly_wrapped_contains_milestones_with_project_names(client, monkeypatch):
    import datetime as dt

    class FakeProjectManager:
        def get_all(self):
            return [
                FakeProject(
                    1,
                    "BigTests",
                    categories={"test": 30, "code": 80, "docs": 30},
                    num_files=100,
                    test_file_ratio=0.2,
                    languages=["Python", "JS", "SQL"],
                    language_share={"Python": 70.0, "JavaScript": 20.0, "SQL": 10.0},
                    author_count=3,
                    collaboration_status="collaborative",
                    total_loc=1200,
                    date_created=dt.datetime(2024, 1, 1),
                    last_modified=dt.datetime(2024, 10, 1),
                ),
            ]

    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)

    res = client.get("/wrapped/yearly")
    assert res.status_code == 200
    data = res.json()

    assert data["ok"] is True
    assert data["wrapped"][0]["year"] == 2024
    assert data["wrapped"][0]["projects_count"] == 1
    assert "vibe_title" in data["wrapped"][0]
    assert isinstance(data["wrapped"][0]["highlights"], list)
    milestones = data["wrapped"][0]["milestones"]
    assert any(m["project"] == "BigTests" for m in milestones)
    assert any(m["badge_id"] == "test_pilot" for m in milestones)

def test_get_config_returns_empty_when_nothing_stored(client, monkeypatch):
    class FakeConfigManager:
        def get_all(self):
            return {}

    monkeypatch.setattr(routes, "ConfigManager", FakeConfigManager)

    res = client.get("/config")
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["config"] == {}


def test_save_config_persists_all_fields(client, monkeypatch):
    stored = {}

    class FakeConfigManager:
        def set(self, key, value):
            stored[key] = value

        def get_all(self):
            return stored

    monkeypatch.setattr(routes, "ConfigManager", FakeConfigManager)

    payload = {"name": "Ada Lovelace", "email": "ada@test.com", "phone": "555-1234", "github": "ada-lv", "linkedin": "ada-lovelace"}
    res = client.post("/config", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert stored["name"] == "Ada Lovelace"
    assert stored["email"] == "ada@test.com"
    assert stored["phone"] == "555-1234"
    assert stored["github"] == "ada-lv"
    assert stored["linkedin"] == "ada-lovelace"


def test_save_config_skips_empty_fields(client, monkeypatch):
    stored = {}

    class FakeConfigManager:
        def set(self, key, value):
            stored[key] = value

        def get_all(self):
            return stored

    monkeypatch.setattr(routes, "ConfigManager", FakeConfigManager)

    payload = {"name": "Ada Lovelace", "email": "", "phone": None, "github": "   ", "linkedin": None}
    res = client.post("/config", json=payload)
    assert res.status_code == 200
    assert "name" in stored
    assert "email" not in stored
    assert "phone" not in stored
    assert "github" not in stored
    assert "linkedin" not in stored


def test_save_config_required_fields_only(client, monkeypatch):
    stored = {}

    class FakeConfigManager:
        def set(self, key, value):
            stored[key] = value

        def get_all(self):
            return stored

    monkeypatch.setattr(routes, "ConfigManager", FakeConfigManager)

    payload = {"name": "Ada Lovelace", "email": "ada@test.com", "phone": "555-1234"}
    res = client.post("/config", json=payload)
    assert res.status_code == 200
    assert stored == {"name": "Ada Lovelace", "email": "ada@test.com", "phone": "555-1234"}

def test_delete_project_success(client, monkeypatch):
    class FakeProject:
        def __init__(self, id, name):
            self.id = id
            self.name = name

    class FakeProjectManager:
        def get(self, id):
            return FakeProject(id, f"Project{id}") if id == 42 else None
        def delete(self, id):
            return True

    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)

    res = client.delete("/projects/42")
    assert res.status_code == 204

def test_delete_project_not_found(client, monkeypatch):
    class FakeProjectManager:
        def get(self, id):
            return None
        def delete(self, id):
            return False

    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)

    res = client.delete("/projects/99")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_delete_report_success(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    class FakeReport:
        def __init__(self, id):
            self.id = id
            self.title = "Report"

    class FakeReportManager:
        def get_report(self, id):
            return FakeReport(id) if id == 7 else None
        def delete_report(self, id):
            return True

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.delete("/reports/7")
    assert res.status_code == 204

def test_delete_report_not_found(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    class FakeReportManager:
        def get_report(self, id):
            return None
        def delete_report(self, id):
            return False

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.delete("/reports/99")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_get_portfolio_rejects_resume_report_kind(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    class FakeReport:
        report_kind = "resume"
        projects = []

    class FakeReportManager:
        def get_report(self, id):
            return FakeReport() if id == 1 else None

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.get("/portfolio/1")
    assert res.status_code == 400
    assert "only supports 'portfolio'" in res.json()["detail"]


def test_get_resume_context_rejects_portfolio_report_kind(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    class FakeReport:
        report_kind = "portfolio"

    class FakeReportManager:
        def get_report(self, id):
            return FakeReport() if id == 1 else None

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.get("/resume/context/1")
    assert res.status_code == 400
    assert "only supports 'resume'" in res.json()["detail"]

def test_get_portfolio_requires_consent(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return False

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)

    res = client.get("/portfolio/1")
    assert res.status_code == 403
    assert "consent" in res.json()["detail"].lower()

def test_export_portfolio_requires_consent(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return False

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)

    res = client.post("/portfolio/export", json={
        "report_id": 1,
        "output_name": "portfolio.pdf"
    })

    assert res.status_code == 403
    assert "consent" in res.json()["detail"].lower()

def test_edit_portfolio_requires_consent(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return False

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)

    res = client.post("/portfolio/1/edit", json={
        "title": "New Title",
        "notes": "Updated notes"
    })
    assert res.status_code == 403
    assert "consent" in res.json()["detail"].lower()

#Test for GET /reports
def test_list_reports_success(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    class FakeSavedReport:
        def __init__(self, id, title, project_count):
            self.id = id
            self.title = title
            self.date_created = datetime(2025, 1, 1)
            self.sort_by = "resume_score"
            self.notes = "notes"
            self.project_count = project_count
            self.report_kind = "resume"

    class FakeReportManager:
        def list_reports(self):
            return [
                FakeSavedReport(1, "Report A", 2),
                FakeSavedReport(2, "Report B", 1),
            ]

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.get("/reports")
    assert res.status_code == 200

    data = res.json()
    assert len(data["reports"]) == 2
    assert data["reports"][0]["id"] == 1
    assert data["reports"][0]["title"] == "Report A"
    assert data["reports"][1]["id"] == 2
    assert data["reports"][1]["title"] == "Report B"

# Tests for GET /reports/{id}
def test_get_report_success(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    class FakeSavedReport:
        def __init__(self):
            self.id = 5
            self.title = "My Report"
            self.date_created = datetime(2025, 1, 1)
            self.sort_by = "resume_score"
            self.notes = "hello"
            self.project_count = 3
            self.report_kind = "resume"

    class FakeReportManager:
        def get_report(self, id):
            return FakeSavedReport() if id == 5 else None

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.get("/reports/5")
    assert res.status_code == 200

    data = res.json()
    assert data["report"]["id"] == 5
    assert data["report"]["title"] == "My Report"
    assert data["report"]["project_count"] == 3

#Test for GET /reports/{id} not found
def test_get_report_not_found(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    class FakeReportManager:
        def get_report(self, id):
            return None

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.get("/reports/999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

#Test for POST /reports success
def test_create_report_success(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    class FakeProjectManager:
        def get(self, pid):
            return FakeProject(
                pid,
                f"Proj{pid}",
                bullets=["Built backend APIs"],
                summary="Worked on backend",
                resume_score=4.5,
                portfolio_details=None,
                languages=["Python"],
                language_share={"Python": 100.0},
                frameworks=["FastAPI"],
                date_created=datetime(2025, 1, 1),
                last_modified=datetime(2025, 2, 1),
                collaboration_status="collaborative",
                file_path="fake/path.zip",
            )

    class FakeSavedReport:
        def __init__(self):
            self.id = 10
            self.title = "My Report"
            self.date_created = datetime(2025, 2, 2)
            self.sort_by = "resume_score"
            self.notes = "notes"
            self.project_count = 2
            self.report_kind = "resume"

    class FakeReportManager:
        def create_report(self, report):
            return 10

        def get_report(self, report_id):
            return FakeSavedReport()

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.post("/reports", json={
        "title": "My Report",
        "sort_by": "resume_score",
        "notes": "notes",
        "project_ids": [1, 2]
    })

    assert res.status_code == 201
    data = res.json()
    assert data["report"]["id"] == 10
    assert data["report"]["title"] == "My Report"

#Test that POST /reports project not found
def test_create_report_project_not_found(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    class FakeProjectManager:
        def get(self, pid):
            return None

    class FakeReportManager:
        pass

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.post("/reports", json={
        "title": "My Report",
        "sort_by": "resume_score",
        "notes": "",
        "project_ids": [99]
    })

    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

def test_upload_thumbnail_success(client, tmp_path, monkeypatch):
    class FakeProjectManager:
        def __init__(self):
            self.p = Project(
                id=1,
                name="ThumbTest",
                file_path="dummy.zip",
                languages=[],
                frameworks=[],
                skills_used=[],
            )

        def get(self, id):
            return self.p if id == 1 else None

        def set(self, project):
            self.p = project

    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)

    monkeypatch.chdir(tmp_path)

    file_bytes = b"fake image bytes"
    response = client.post(
        "/projects/1/thumbnail",
        files={"file": ("thumb.png", io.BytesIO(file_bytes), "image/png")},
    )

    assert response.status_code == 200



def test_upload_thumbnail_invalid_extension(client):
    pm = ProjectManager()
    p = Project(
        name="BadExt",
        file_path="dummy.zip",
        languages=[],
        frameworks=[],
        skills_used=[],
    )
    pm.set(p)

    response = client.post(
        f"/projects/{p.id}/thumbnail",
        files={"file": ("thumb.txt", io.BytesIO(b"nope"), "text/plain")},
    )

    assert response.status_code == 400
    assert "Invalid image format" in response.json()["detail"]


def test_upload_thumbnail_project_not_found(client):
    response = client.post(
        "/projects/999999/thumbnail",
        files={"file": ("thumb.png", io.BytesIO(b"fake"), "image/png")},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found."


def test_serve_thumbnail_success(client, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    filename = "test_thumb.png"
    file_path = tmp_path / "thumbnails" / filename
    file_path.parent.mkdir(exist_ok=True)
    file_path.write_bytes(b"imagebytes")

    response = client.get(f"/thumbnails/{filename}")

    assert response.status_code == 200
    assert response.content == b"imagebytes"


def test_serve_thumbnail_not_found(client):
    response = client.get("/thumbnails/does_not_exist.png")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

# ── GET /resume/context/{id} ──────────────────────────────────────────────────

def test_get_resume_context_success(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    project = ReportProject(
        project_name="MyApp",
        resume_score=4.0,
        bullets=["Built REST API", "Improved performance by 40%"],
        languages=["Python", "JavaScript"],
        frameworks=["FastAPI", "React"],
        date_created=datetime(2024, 1, 1),
        last_modified=datetime(2024, 6, 1),
    )
    report = Report(
        id=1,
        title="Dev Resume",
        date_created=datetime(2025, 1, 1),
        sort_by="resume_score",
        projects=[project],
    )

    class FakeReportManager:
        def get_report(self, id):
            return report if id == 1 else None

    class FakeConfigManager:
        def get(self, key, default=None):
            data = {
                "name": "Dale Smith",
                "email": "dale@example.com",
                "phone": "250-555-0100",
                "github": "dalesmith",
                "linkedin": "dale-smith",
                "education": [],
                "experience": [],
                "skills": {},
            }
            return data.get(key, default)

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)
    monkeypatch.setattr(routes, "ConfigManager", FakeConfigManager)

    res = client.get("/resume/context/1")
    assert res.status_code == 200

    data = res.json()
    assert data["name"] == "Dale Smith"
    assert data["email"] == "dale@example.com"
    assert len(data["projects"]) == 1
    assert data["projects"][0]["name"] == "MyApp"
    assert data["projects"][0]["bullets"] == ["Built REST API", "Improved performance by 40%"]
    assert "Python" in data["projects"][0]["stack"]


def test_get_resume_context_not_found(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    class FakeReportManager:
        def get_report(self, id):
            return None

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.get("/resume/context/999")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_get_resume_context_requires_consent(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return False

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)

    res = client.get("/resume/context/1")
    assert res.status_code == 403
    assert "consent" in res.json()["detail"].lower()


# ── PATCH /reports/{id}/projects/{project_name} ───────────────────────────────

def test_patch_report_project_updates_bullets(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    project = ReportProject(
        project_name="MyApp",
        bullets=["Old bullet"],
        languages=["Python"],
        frameworks=[],
    )
    report = Report(
        id=1,
        title="Resume",
        date_created=datetime(2025, 1, 1),
        sort_by="resume_score",
        projects=[project],
    )

    updated = {}

    class FakeReportManager:
        def get_report(self, id):
            return report if id == 1 else None

        def update_report(self, r):
            updated["bullets"] = r.projects[0].bullets
            return True

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.patch("/reports/1/projects/MyApp", json={"bullets": ["New bullet A", "New bullet B"]})
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert updated["bullets"] == ["New bullet A", "New bullet B"]


def test_update_portfolio_mode_success(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self): return True

    report = Report(id=11, title="R", date_created=datetime(2025,1,1), sort_by="resume_score", projects=[], notes=None, report_kind="portfolio")

    class FakeReportManager:
        def get_report(self, id): return report if id == 11 else None
        def update_report(self, updated): return True

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.patch("/portfolio/11/mode", json={"mode": "public"})
    assert res.status_code == 200
    assert res.json()["portfolio"]["portfolio_mode"] == "public"

def test_update_portfolio_project_rejects_when_public(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self): return True

    rp = ReportProject(project_name="ProjA", portfolio_details=PortfolioDetails())
    report = Report(id=12, title="R", date_created=datetime(2025,1,1), sort_by="resume_score", projects=[rp], notes=None, report_kind="portfolio")
    report.portfolio_mode = "public"

    class FakeReportManager:
        def get_report(self, id): return report if id == 12 else None
        def update_report(self, updated): return True

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.patch("/portfolio/12/projects/ProjA", json={"custom_overview": "New text"})
    assert res.status_code == 409


def test_patch_report_project_updates_stack(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    project = ReportProject(
        project_name="MyApp",
        bullets=[],
        languages=["Python"],
        frameworks=["Django"],
    )
    report = Report(
        id=2,
        title="Resume",
        date_created=datetime(2025, 1, 1),
        sort_by="resume_score",
        projects=[project],
    )

    updated = {}

    class FakeReportManager:
        def get_report(self, id):
            return report if id == 2 else None

        def update_report(self, r):
            updated["languages"] = r.projects[0].languages
            updated["frameworks"] = r.projects[0].frameworks
            return True

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.patch("/reports/2/projects/MyApp", json={
        "stack_languages": ["Python", "TypeScript"],
        "stack_frameworks": ["FastAPI"],
    })
    assert res.status_code == 200
    assert updated["languages"] == ["Python", "TypeScript"]
    assert updated["frameworks"] == ["FastAPI"]

def test_update_portfolio_project_customizations_success(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self): return True

    rp = ReportProject(project_name="ProjA", portfolio_details=PortfolioDetails(overview="Old"))
    report = Report(id=13, title="R", date_created=datetime(2025,1,1), sort_by="resume_score", projects=[rp], notes=None, report_kind="portfolio")
    report.portfolio_mode = "private"

    class FakeReportManager:
        def get_report(self, id): return report if id == 13 else None
        def update_report(self, updated): return True

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.patch("/portfolio/13/projects/ProjA", json={"custom_overview": "Updated", "custom_achievements": ["A1", "A2"]})
    assert res.status_code == 200
    payload = res.json()
    assert payload["portfolio"]["projects"][0]["portfolio_customizations"]["custom_overview"] == "Updated"


def test_patch_report_project_not_found(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    report = Report(
        id=1,
        title="Resume",
        date_created=datetime(2025, 1, 1),
        sort_by="resume_score",
        projects=[],
    )

    class FakeReportManager:
        def get_report(self, id):
            return report if id == 1 else None

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.patch("/reports/1/projects/NonExistent", json={"bullets": ["x"]})
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_publish_and_unpublish_portfolio(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self): return True

    report = Report(id=14, title="R", date_created=datetime(2025,1,1), sort_by="resume_score", projects=[], notes=None, report_kind="portfolio")

    class FakeReportManager:
        def get_report(self, id): return report if id == 14 else None
        def update_report(self, updated): return True

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    pub = client.post("/portfolio/14/publish")
    assert pub.status_code == 200
    assert pub.json()["portfolio"]["portfolio_mode"] == "public"
    assert pub.json()["portfolio"]["portfolio_published_at"] is not None

    unpub = client.post("/portfolio/14/unpublish")
    assert unpub.status_code == 200
    assert unpub.json()["portfolio"]["portfolio_mode"] == "private"
    assert unpub.json()["portfolio"]["portfolio_published_at"] is None


def test_patch_report_project_report_not_found(client, monkeypatch):
    class FakeConsentManager:
        def has_user_consented(self):
            return True

    class FakeReportManager:
        def get_report(self, id):
            return None

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)
    monkeypatch.setattr(routes, "ReportManager", FakeReportManager)

    res = client.patch("/reports/99/projects/MyApp", json={"bullets": ["x"]})
    assert res.status_code == 404


# ── POST /config/set ──────────────────────────────────────────────────────────

def test_config_set_stores_string_value(client, monkeypatch):
    stored = {}

    class FakeConfigManager:
        def set(self, key, value):
            stored[key] = value

    monkeypatch.setattr(routes, "ConfigManager", FakeConfigManager)

    res = client.post("/config/set", json={"key": "name", "value": "Ada Lovelace"})
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert stored["name"] == "Ada Lovelace"


def test_config_set_stores_list_value(client, monkeypatch):
    """Education/experience are stored as lists — must round-trip correctly."""
    stored = {}

    class FakeConfigManager:
        def set(self, key, value):
            stored[key] = value

    monkeypatch.setattr(routes, "ConfigManager", FakeConfigManager)

    education = [{"school": "UBC Okanagan", "degree": "BSc Computer Science", "location": "Kelowna, BC", "dates": "2021 - 2025"}]
    res = client.post("/config/set", json={"key": "education", "value": education})
    assert res.status_code == 200
    assert stored["education"] == education


def test_config_set_stores_dict_value(client, monkeypatch):
    stored = {}

    class FakeConfigManager:
        def set(self, key, value):
            stored[key] = value

    monkeypatch.setattr(routes, "ConfigManager", FakeConfigManager)

    skills = {"Languages": ["Python", "JavaScript"], "Frameworks": ["FastAPI", "React"]}
    res = client.post("/config/set", json={"key": "skills", "value": skills})
    assert res.status_code == 200
    assert stored["skills"] == skills
