import pytest
from unittest.mock import MagicMock
from datetime import datetime

from src.managers.ReportProjectManager import ReportProjectManager
from src.models.ReportProject import ReportProject


@pytest.fixture
def mock_storage(monkeypatch):
    monkeypatch.setattr("src.managers.ReportProjectManager.StorageManager.set", MagicMock())
    monkeypatch.setattr("src.managers.ReportProjectManager.StorageManager.get", MagicMock())
    monkeypatch.setattr("src.managers.ReportProjectManager.StorageManager.get_all", MagicMock())
    monkeypatch.setattr("src.managers.ReportProjectManager.StorageManager._deserialize_row", lambda self, x: x)
    monkeypatch.setattr("src.managers.ReportProjectManager.StorageManager._get_connection", MagicMock())
    return True


@pytest.fixture
def rpm(mock_storage):
    return ReportProjectManager(db_path=":memory:")


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


def test_set_from_report_project(rpm):
    rpm.set = MagicMock()
    proj = make_project("Alpha")

    rpm.set_from_report_project(10, proj)

    rpm.set.assert_called_once()
    row = rpm.set.call_args[0][0]

    assert row["report_id"] == 10
    assert row["project_name"] == "Alpha"


def test_get_success(rpm, monkeypatch):
    now = datetime.now().isoformat()

    monkeypatch.setattr(
        "src.managers.ReportProjectManager.StorageManager.get",
        MagicMock(return_value={
            "project_name": "ProjA",
            "resume_score": 2.0,
            "bullets": [],
            "summary": "test",
            "languages": [],
            "language_share": {},
            "frameworks": [],
            "date_created": now,
            "last_modified": now,
            "collaboration_status": "team",
        })
    )

    proj = rpm.get(5)

    assert proj.project_name == "ProjA"
    assert proj.resume_score == 2.0
    assert proj.collaboration_status == "team"


def test_get_not_found(rpm, monkeypatch):
    monkeypatch.setattr(
        "src.managers.ReportProjectManager.StorageManager.get",
        MagicMock(return_value=None)
    )
    assert rpm.get(99) is None


def test_get_all_for_report(rpm, monkeypatch):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    rows = [
        (1, 10, "A", 1.0, "[]", "sum", "[]", "{}", "[]", None, None, "individual"),
        (2, 10, "B", 2.0, "[]", "sum2", "[]", "{}", "[]", None, None, "team"),
    ]

    mock_cursor.fetchall.return_value = rows
    mock_conn.cursor.return_value = mock_cursor
    rpm._get_connection.return_value.__enter__.return_value = mock_conn

    monkeypatch.setattr(
        rpm.__class__,
        "columns_list",
        property(lambda self: rpm.columns.split(", "))
    )

    projects = rpm.get_all_for_report(10)

    assert len(projects) == 2
    assert projects[0].project_name == "A"
    assert projects[1].project_name == "B"


def test_delete_by_name(rpm):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 1

    mock_conn.cursor.return_value = mock_cursor
    rpm._get_connection.return_value.__enter__.return_value = mock_conn

    ok = rpm.delete_by_name(10, "ProjX")
    assert ok is True


def test_delete_by_name_no_match(rpm):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 0

    mock_conn.cursor.return_value = mock_cursor
    rpm._get_connection.return_value.__enter__.return_value = mock_conn

    ok = rpm.delete_by_name(10, "Missing")
    assert ok is False


def test_delete_all_for_report(rpm):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.rowcount = 3

    mock_conn.cursor.return_value = mock_cursor
    rpm._get_connection.return_value.__enter__.return_value = mock_conn

    deleted = rpm.delete_all_for_report(10)
    assert deleted == 3


def test_get_all_generator(rpm, monkeypatch):
    monkeypatch.setattr(
        "src.managers.ReportProjectManager.StorageManager.get_all",
        MagicMock(return_value=[
            {
                "project_name": "A",
                "resume_score": 1.0,
                "bullets": [],
                "summary": "",
                "languages": [],
                "language_share": {},
                "frameworks": [],
                "date_created": None,
                "last_modified": None,
                "collaboration_status": "individual",
            },
            {
                "project_name": "B",
                "resume_score": 2.0,
                "bullets": [],
                "summary": "",
                "languages": [],
                "language_share": {},
                "frameworks": [],
                "date_created": None,
                "last_modified": None,
                "collaboration_status": "team",
            },
        ])
    )

    results = list(rpm.get_all())

    assert len(results) == 2
    assert results[0].project_name == "A"
    assert results[1].project_name == "B"
