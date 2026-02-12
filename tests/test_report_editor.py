import pytest
from types import SimpleNamespace

from src.services.ReportEditor import ReportEditor


# -------------------------
# Helpers / Fakes
# -------------------------

class FakeConfigManager:
    def __init__(self, initial=None):
        self._data = dict(initial or {})

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


def _feed_inputs(monkeypatch, inputs):
    it = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda _="": next(it))


def _make_report():
    # Minimal shape your ReportEditor needs: report.projects list of objects
    # with .project_name and .bullets
    proj1 = SimpleNamespace(project_name="ProjA", bullets=["a1", "a2"], languages=["Python"], frameworks=[])
    proj2 = SimpleNamespace(project_name="ProjB", bullets=["b1"], languages=["Java"], frameworks=[])
    return SimpleNamespace(projects=[proj1, proj2])


# -------------------------
# Tests
# -------------------------

def test_done_immediately(monkeypatch):
    report = _make_report()
    cfg = FakeConfigManager({"name": "Branden"})

    _feed_inputs(monkeypatch, ["q"])

    editor = ReportEditor()
    out = editor.edit_report_cli(report, cfg)

    assert out is True
    assert cfg.get("name") == "Branden"
    assert report.projects[0].project_name == "ProjA"


def test_edit_header_updates_config_and_normalizes_links(monkeypatch):
    report = _make_report()
    cfg = FakeConfigManager({
        "name": "Old",
        "email": "old@email",
        "phone": "111",
        "github": "oldgit",
        "linkedin": "oldli",
    })

    # 1 header -> enter new values -> done
    _feed_inputs(
        monkeypatch,
        [
            "1",
            "New Name",
            "new@email",
            "999",
            "newHandle",                         # github handle
            "https://linkedin.com/in/newLinked",  # linkedin full url
            "q",
        ],
    )

    editor = ReportEditor()
    editor.edit_report_cli(report, cfg)

    assert cfg.get("name") == "New Name"
    assert cfg.get("email") == "new@email"
    assert cfg.get("phone") == "999"

    # Your code stores handle + derived url keys
    assert cfg.get("github") == "newHandle"
    assert cfg.get("github_url") == "https://github.com/newHandle"
    assert cfg.get("linkedin") == "newLinked"
    assert cfg.get("linkedin_url") == "https://linkedin.com/in/newLinked"


def test_rename_project(monkeypatch):
    report = _make_report()
    cfg = FakeConfigManager()

    # 2 projects -> 1 rename -> pick 2 -> name -> back -> done
    _feed_inputs(
        monkeypatch,
        [
            "2",
            "1",
            "2",
            "ProjB_NEW",
            "4",
            "q",
        ],
    )

    editor = ReportEditor()
    editor.edit_report_cli(report, cfg)

    assert report.projects[1].project_name == "ProjB_NEW"
    assert report.projects[0].project_name == "ProjA"


def test_edit_project_bullets_add_edit_delete(monkeypatch):
    report = _make_report()
    cfg = FakeConfigManager()

    # 2 projects -> 2 edit bullets -> pick 1 -> add/edit/delete -> back -> done
    _feed_inputs(
        monkeypatch,
        [
            "2",
            "2",
            "1",

            "2", "a3",          # add bullet
            "1", "1", "a1_edit", # edit bullet #1
            "3", "2",           # delete bullet #2 (original a2)

            "5",                # back bullets
            "4",                # back projects menu
            "q",
        ],
    )

    editor = ReportEditor()
    editor.edit_report_cli(report, cfg)

    assert report.projects[0].bullets == ["a1_edit", "a3"]


def test_reorder_projects(monkeypatch):
    report = _make_report()
    cfg = FakeConfigManager()

    # 2 projects -> 3 reorder -> move 2 to 1 -> q stop reorder -> back -> done
    _feed_inputs(
        monkeypatch,
        [
            "2",
            "3",
            "2,1",
            "q",
            "4",
            "q",
        ],
    )

    editor = ReportEditor()
    editor.edit_report_cli(report, cfg)

    assert report.projects[0].project_name == "ProjB"
    assert report.projects[1].project_name == "ProjA"
