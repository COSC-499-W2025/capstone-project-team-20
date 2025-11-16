import importlib
import pytest

def test_folder_skill_analyzer_has_expected_api():
    """
    This test guards the public surface we rely on:
      - class FolderSkillAnalyzer
      - .analyze_folder(path)
      - .display_analysis_results()
    If the source file accidentally contains the wrong code (e.g., duplicated
    analyze_any), this test will fail and point directly to the issue.
    """
    mod = importlib.import_module("src.analyzers.folder_skill_analyzer")
    assert hasattr(mod, "FolderSkillAnalyzer"), (
        "Expected `FolderSkillAnalyzer` class in src/analyzers/folder_skill_analyzer.py"
    )

    cls = getattr(mod, "FolderSkillAnalyzer")
    inst = cls()

    assert hasattr(inst, "analyze_folder") and callable(inst.analyze_folder), \
        "FolderSkillAnalyzer must define analyze_folder(self, path)"

    assert hasattr(inst, "display_analysis_results") and callable(inst.display_analysis_results), \
        "FolderSkillAnalyzer must define display_analysis_results(self)"
