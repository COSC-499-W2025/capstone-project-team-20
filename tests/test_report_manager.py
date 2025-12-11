import pytest
from unittest.mock import MagicMock
from datetime import datetime

from src.managers.ReportManager import ReportManager
from src.models.Report import Report
from src.models.ReportProject import ReportProject


@pytest.fixture
def mock_storage(monkeypatch):
    monkeypatch.setattr("src.managers.ReportManager.StorageManager.set", MagicMock())
    monkeypatch.setattr("src.managers.ReportManager.StorageManager.get", MagicMock())
    monkeypatch.setattr("src.managers.ReportManager.StorageManager.get_all", MagicMock())
    monkeypatch.setattr("src.managers.ReportManager.StorageManager.delete", MagicMock())
    monkeypatch.setattr("src.managers.ReportManager.StorageManager._get_connection", MagicMock())
    return True


@pytest.fixture
def mock_project_manager(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("src.managers.ReportManager.ReportProjectManager", lambda: mock)
    return mock


@pytest.fixture
def rm(mock_storage, mock_project_manager):
    return ReportManager(db_path=":memory:")


def make_project(name="ProjA"):
    return ReportProject(
        project_name=name,
        resume_score=1.0,
        bullets=[],
        summary="",
        languages=[],
        language_share={},
        frameworks=[],
        date_created=datetime.now(),
        last_modified=datetime.now(),
        collaboration_status="individual",
    )


def make_report(id=None, projects=None):
    return Report(
        id=id,
        title="Test Report",
        date_created=datetime.now(),
        sort_by="resume_score",
        projects=projects or [],
        notes=None,
    )


def test_create_report(rm, mock_project_manager):
    p1 = make_project("A")
    p2 = make_project("B")
    report = make_report(projects=[p1, p2])

    def set_side_effect(row):
        row["id"] = 123

    rm.set = MagicMock(side_effect=set_side_effect)

    rid = rm.create_report(report)

    assert rid == 123
    assert mock_project_manager.set_from_report_project.call_count == 2


def test_get_report(rm, mock_project_manager, monkeypatch):
    now = datetime.now().isoformat()

    # ✅ Correct: mock StorageManager.get, not rm.get
    monkeypatch.setattr(
        "src.managers.ReportManager.StorageManager.get",
        MagicMock(return_value={
            "id": 10,
            "title": "My Report",
            "date_created": now,
            "sort_by": "resume_score",
            "notes": "hello"
        })
    )

    mock_project_manager.get_all_for_report.return_value = [
        make_project("X"),
        make_project("Y")
    ]

    report = rm.get_report(10)

    assert report.id == 10
    assert report.title == "My Report"
    assert len(report.projects) == 2


def test_update_report_metadata(rm):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1

    mock_conn.cursor.return_value = mock_cursor
    rm._get_connection.return_value.__enter__.return_value = mock_conn

    ok = rm.update_report_metadata(5, title="New Title", notes="Updated")

    assert ok is True


def test_update_report_metadata_invalid(rm):
    ok = rm.update_report_metadata(5, foo="bar")
    assert ok is False


def test_add_project_to_report(rm, mock_project_manager):
    proj = make_project("Z")
    ok = rm.add_project_to_report(7, proj)
    assert ok is True


def test_add_project_to_report_failure(rm, mock_project_manager):
    mock_project_manager.set_from_report_project.side_effect = Exception("fail")
    ok = rm.add_project_to_report(7, make_project("Z"))
    assert ok is False


def test_remove_project_from_report(rm, mock_project_manager):
    mock_project_manager.delete_by_name.return_value = True
    ok = rm.remove_project_from_report(3, "ProjX")
    assert ok is True


def test_delete_report(rm):
    rm.delete = MagicMock(return_value=True)
    ok = rm.delete_report(9)
    assert ok is True


def test_list_reports(rm, mock_project_manager, monkeypatch):
    now = datetime.now().isoformat()

    # ✅ Correct: mock StorageManager.get_all, not rm.get_all
    monkeypatch.setattr(
        "src.managers.ReportManager.StorageManager.get_all",
        MagicMock(return_value=[
            {"id": 1, "title": "R1", "date_created": now, "sort_by": "resume_score", "notes": None},
            {"id": 2, "title": "R2", "date_created": now, "sort_by": "resume_score", "notes": None},
        ])
    )

    mock_project_manager.get_all_for_report.side_effect = [
        [make_project("A")],
        [make_project("B"), make_project("C")]
    ]

    reports = rm.list_reports()

    assert len(reports) == 2
    assert len(reports[0].projects) == 1
    assert len(reports[1].projects) == 2


def test_list_reports_summary(rm):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_cursor.fetchall.return_value = [
        (1, "R1", "2024-01-01T00:00:00", 2),
        (2, "R2", "2024-01-02T00:00:00", 0),
    ]

    mock_conn.cursor.return_value = mock_cursor
    rm._get_connection.return_value.__enter__.return_value = mock_conn

    summaries = rm.list_reports_summary()

    assert len(summaries) == 2
    assert summaries[0]["project_count"] == 2
    assert summaries[1]["project_count"] == 0


def test_get_all_generator(rm):
    rm.list_reports = MagicMock(return_value=[
        make_report(id=1),
        make_report(id=2),
    ])

    results = list(rm.get_all())

    assert len(results) == 2
    assert results[0].id == 1
    assert results[1].id == 2
