import copy
import pytest

from src.services.ResumeVariantEditor import ResumeVariantEditor


def _make_base_context():
    return {
        "name": "Branden",
        "email": "b@example.com",
        "phone": "111",
        "github_url": "https://github.com/branden6",
        "github_display": "github.com/branden6",
        "linkedin_url": "https://linkedin.com/in/brandenkennedy1",
        "linkedin_display": "linkedin.com/in/brandenkennedy1",
        "education": [],
        "experience": [],
        "projects": [
            {
                "name": "ProjA",
                "stack": "Python",
                "dates": "Jan 2026 - Feb 2026",
                "bullets": ["a1", "a2"],
            },
            {
                "name": "ProjB",
                "stack": "Java",
                "dates": "Mar 2026 - Apr 2026",
                "bullets": ["b1"],
            },
        ],
        "skills": {"Languages": ["Python", "Java"]},
    }


def _feed_inputs(monkeypatch, inputs):
    it = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda _="": next(it))


def test_editor_does_not_mutate_original(monkeypatch):
    base = _make_base_context()
    base_before = copy.deepcopy(base)

    # q immediately -> should return a deepcopy, but no changes
    _feed_inputs(monkeypatch, ["q"])

    editor = ResumeVariantEditor()
    edited = editor.edit_variant_cli(base)

    assert base == base_before, "Base context should not be mutated"
    assert edited == base_before, "Edited context should equal base if no edits are made"
    assert edited is not base, "Should return a new object"


def test_editor_edit_header(monkeypatch):
    base = _make_base_context()
    editor = ResumeVariantEditor()

    _feed_inputs(
        monkeypatch,
        [
            "1",            # menu: edit header
            "New Name",     # name
            "new@email",    # email
            "999",          # phone
            "newHandle",    # github (handle)
            "newLinked",    # linkedin (handle)
            "q",            # done
        ],
    )

    edited = editor.edit_variant_cli(base)

    assert edited["name"] == "New Name"
    assert edited["email"] == "new@email"
    assert edited["phone"] == "999"

    # derived fields should update together
    assert edited["github_url"] == "https://github.com/newHandle"
    assert edited["github_display"] == "github.com/newHandle"
    assert edited["linkedin_url"] == "https://linkedin.com/in/newLinked"
    assert edited["linkedin_display"] == "linkedin.com/in/newLinked"



def test_editor_edit_project_info(monkeypatch):
    base = _make_base_context()
    editor = ResumeVariantEditor()

    _feed_inputs(
    monkeypatch,
    [
        "2",          # main menu: Edit projects (info + bullets)
        "1",          # projects menu: Edit project info
        "2",          # pick ProjB
        "ProjB_NEW",  # name
        "Java, SQL",  # stack
        "2025-2026",  # dates
        "4",          # back (projects menu)
        "q",          # done (main menu)
    ],
)


    edited = editor.edit_variant_cli(base)

    assert edited["projects"][1]["name"] == "ProjB_NEW"
    assert edited["projects"][1]["stack"] == "Java, SQL"
    assert edited["projects"][1]["dates"] == "2025-2026"
    assert edited["projects"][0]["name"] == "ProjA"



def test_editor_edit_bullets_add_edit_delete_reorder(monkeypatch):
    base = _make_base_context()
    editor = ResumeVariantEditor()

    # Inside bullets menu:
    # 2 add "a3"
    # 1 edit bullet 1 -> "a1_edit"
    # 4 move bullet 3 up (u) -> moves a3 above a2
    # 3 delete bullet 2 (after reorder)
    # 5 back, q done
    _feed_inputs(
    monkeypatch,
    [
        "2",     # main menu: Edit projects
        "2",     # projects menu: Edit project bullets
        "1",     # pick project 1 (ProjA)

        "2",     # add bullet
        "a3",    # new bullet text

        "1",     # edit bullet
        "1",     # bullet #1
        "a1_edit",

        "4",     # move bullet
        "3",     # bullet #3 (a3)
        "u",     # up

        "3",     # delete bullet
        "2",     # delete bullet #2 (after reorder)

        "5",     # back (bullets menu)
        "4",     # back (projects menu)
        "q",     # done (main menu)
    ],
)


    edited = editor.edit_variant_cli(base)
    bullets = edited["projects"][0]["bullets"]

    # Start: ["a1","a2"]
    # add a3 => ["a1","a2","a3"]
    # edit #1 => ["a1_edit","a2","a3"]
    # move #3 up => ["a1_edit","a3","a2"]
    # delete #2 => ["a1_edit","a2"]
    assert bullets == ["a1_edit", "a2"]
