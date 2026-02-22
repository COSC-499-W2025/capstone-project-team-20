import io
import pytest
from fastapi.testclient import TestClient

import src.api.routes as routes
from src.api.api_main import app


# Shared Test Client, fake HTTP client connected to FastAPI app.
@pytest.fixture
def client():
    return TestClient(app)


# Fake Project
class FakeProject:
    def __init__(self, id, name, skills_used=None, categories=None, num_files=0, test_file_ratio=0.0, languages=None, language_share=None, author_count=1, collaboration_status="individual", size_kb=0, total_loc=0, date_created=None, last_modified=None,):
        self.id = id
        self.name = name
        self.skills_used = skills_used or []
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


# /privacy-consent test. calling POST /privacy-consent?consent=true returns 200
def test_privacy_consent_sets_value(client, monkeypatch):
    calls = {}

    class FakeConsentManager:
        def set_consent(self, consent: bool):
            calls["consent"] = consent

    monkeypatch.setattr(routes, "ConsentManager", FakeConsentManager)

    res = client.post("/privacy-consent", params={"consent": "true"})
    assert res.status_code == 200

    data = res.json()
    assert data["ok"] is True
    assert data["consent"] is True
    assert calls["consent"] is True


# /projects (list) test. testing GET /project
def test_get_projects_list(client, monkeypatch):
    class FakeProjectManager:
        def get_all(self):
            return [FakeProject(1, "A"), FakeProject(2, "B")]

    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)

    res = client.get("/projects")
    assert res.status_code == 200

    data = res.json()
    assert data["ok"] is True
    assert data["projects"] == [
        {"id": 1, "name": "A"},
        {"id": 2, "name": "B"},
    ]


#/projects/{id} test. GET /projects/5 test.
def test_get_project_found(client, monkeypatch):
    class FakeProjectManager:
        def get(self, id: int):
            return FakeProject(id, "CoolProj", skills_used=["Python"])

    monkeypatch.setattr(routes, "ProjectManager", FakeProjectManager)

    res = client.get("/projects/5")
    assert res.status_code == 200

    data = res.json()
    assert data["ok"] is True
    assert data["project"]["id"] == 5
    assert data["project"]["name"] == "CoolProj"


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

        def initialize_projects(self):
            return [FakeProject(1, "Proj1"), FakeProject(2, "Proj2")]

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

def test_upload_project_invalid_zip_returns_400(client, monkeypatch):
    # Simulate invalid zip (no root folders)
    monkeypatch.setattr(routes, "parse_zip_to_project_folders", lambda _: [])

    files = {"zip_file": ("bad.zip", io.BytesIO(b"bad"), "application/zip")}
    res = client.post("/projects/upload", files=files)

    assert res.status_code == 400
    assert "Zip parsed no projects" in res.json()["detail"]

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
    assert data["ok"] is True

    as_map = {item["badge_id"]: item for item in data["badges"]}
    assert as_map["test_pilot"]["earned"] is True
    assert as_map["test_pilot"]["project"]["name"] == "TestsHeavy"
    assert as_map["docs_guardian"]["project"]["name"] == "DocsHeavy"


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