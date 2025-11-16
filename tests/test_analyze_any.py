import os
from pathlib import Path
import types
import builtins
import importlib

import pytest


@pytest.fixture
def tmp_zip_workspace(tmp_path: Path):
    """
    Create a fake extracted-zip workspace:
      /work
        /alpha/.git/      -> should be considered a repo root (skipped for folder analyzer)
        /alpha/app.py
        /beta/utils.js    -> non-git folder, must be analyzed by FolderSkillAnalyzer
        /__MACOSX/trash   -> must be ignored
    """
    work = tmp_path / "work"
    (work / "alpha" / ".git").mkdir(parents=True)
    (work / "alpha" / "app.py").write_text("print('hello')\n")
    (work / "beta").mkdir()
    (work / "beta" / "utils.js").write_text("export const x = 1;\n")
    (work / "__MACOSX").mkdir()
    (work / "__MACOSX" / "trash").write_text("ignore me")
    return work


def _install_fakes_in_module(module, repo_roots):
    """
    Monkeypatch the module namespace to use fake analyzers and extract_zip.
    Collect calls made by analyze_zip_any.
    """
    calls = types.SimpleNamespace()
    calls.git_find_called = False
    calls.folder_analyzed = []

    class FakeGitRepoAnalyzer:
        def __init__(self): pass
        def _find_and_analyze_repos(self, temp_dir):
            calls.git_find_called = True
            # simulate discovery of repo roots (e.g., .../alpha)
            return repo_roots
        def display_analysis_results(self):
            print("[FakeGitRepoAnalyzer] displayed")

    class FakeFolderSkillAnalyzer:
        def __init__(self): pass
        def analyze_folder(self, root):
            calls.folder_analyzed.append(os.fspath(root))
        def display_analysis_results(self):
            print("[FakeFolderSkillAnalyzer] displayed")

    def fake_extract_zip(zip_path: str):
        # analyze_any will receive the path returned by this function.
        # The test injects the path via a closure; see monkeypatch below.
        return module.__test_work_dir  # type: ignore[attr-defined]

    module.GitRepoAnalyzer = FakeGitRepoAnalyzer
    module.FolderSkillAnalyzer = FakeFolderSkillAnalyzer
    module.extract_zip = fake_extract_zip
    return calls


def test_analyze_zip_any_calls_both_paths(tmp_zip_workspace, monkeypatch):
    """
    Verifies:
      - extract_zip() is used
      - GitRepoAnalyzer._find_and_analyze_repos is invoked
      - Only non-git dirs (excluding __MACOSX) are sent to FolderSkillAnalyzer.analyze_folder
      - Both sections are printed
    """
    # Import the target module fresh so our monkeypatch lands on the module object.
    import src.analyzers.analyze_any as analyze_any

    # Inject the temp work dir path so fake_extract_zip can return it.
    analyze_any.__test_work_dir = tmp_zip_workspace  # type: ignore[attr-defined]

    # Prepare repo roots to simulate that /alpha is a discovered git repo.
    repo_roots = [os.fspath(tmp_zip_workspace / "alpha")]
    calls = _install_fakes_in_module(analyze_any, repo_roots)

    # Run
    from src.analyzers.analyze_any import analyze_zip_any
    # Any string is accepted; our fake_extract_zip ignores it and returns __test_work_dir.
    analyze_zip_any("ignored.zip")

    # Assertions
    assert calls.git_find_called is True

    analyzed = set(calls.folder_analyzed)
    assert os.fspath(tmp_zip_workspace / "beta") in analyzed, "non-git /beta must be analyzed"
    assert not any("__MACOSX" in p for p in analyzed), "should not analyze __MACOSX"
    # ensure repo root wasn't analyzed as non-git
    assert os.fspath(tmp_zip_workspace / "alpha") not in analyzed

def test_analyze_zip_any_prints_sections(tmp_zip_workspace, capsys):
    import src.analyzers.analyze_any as analyze_any
    analyze_any.__test_work_dir = tmp_zip_workspace  # type: ignore[attr-defined]

    calls = _install_fakes_in_module(analyze_any, [os.fspath(tmp_zip_workspace / "alpha")])

    from src.analyzers.analyze_any import analyze_zip_any
    analyze_zip_any("ignored.zip")
    out = capsys.readouterr().out

    assert "=== GIT REPOSITORIES ===" in out
    assert "=== NON-GIT FOLDERS ===" in out
    assert "[FakeGitRepoAnalyzer] displayed" in out
    assert "[FakeFolderSkillAnalyzer] displayed" in out
