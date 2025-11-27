from pathlib import Path
from unittest.mock import MagicMock, patch

from src.analyzers.RepoProjectBuilder import RepoProjectBuilder


# --- Dummy ZIP tree structure (ProjectFolder tree) ------------------

class DummyFile:
    def __init__(self, name, size=100, modified=None):
        self.file_name = name
        self.size = size
        self.last_modified = modified


class DummyFolder:
    def __init__(self, name, children=None, subdir=None):
        self.name = name
        self.children = children or []
        self.subdir = subdir or []

def _make_folder_tree():
    """
    Create a fake ZIP folder tree:

    root
    └── myrepo   (folder)
        ├── a.py
        └── b.py
    """
    repo_folder = DummyFolder(
        name="MyRepo",
        children=[
            DummyFile("a.py"),
            DummyFile("b.py")
        ]
    )

    root = DummyFolder(
        name="root",
        children=[],
        subdir=[repo_folder]
    )

    return root, repo_folder


# build a fake ZIP tree with folder names matching repo folders


def build_zip_tree():
    """
    ZIP structure:
        root/
            RepoA/
                fileA1
                fileA2
            RepoB/
                fileB1
    """
    repoA = DummyFolder("RepoA", children=[
        DummyFile("fileA1.py"),
        DummyFile("fileA2.js"),
    ])

    repoB = DummyFolder("RepoB", children=[
        DummyFile("fileB1.java"),
    ])

    root = DummyFolder("root", subdir=[repoA, repoB])
    return root, repoA, repoB



def test_find_folder_by_name():
    root, repoA, repoB = build_zip_tree()
    builder = RepoProjectBuilder(root)

    assert builder._find_folder_by_name(root, "RepoA") is repoA
    assert builder._find_folder_by_name(root, "RepoB") is repoB
    assert builder._find_folder_by_name(root, "DoesNotExist") is None



# builds a project object when contributions, metadata, languages are mocked

@patch("src.analyzers.RepoProjectBuilder.detect_language_per_file")
@patch("src.analyzers.RepoProjectBuilder.analyze_language_share")
@patch("src.analyzers.RepoProjectBuilder.ContributionAnalyzer")
@patch("src.analyzers.RepoProjectBuilder.ProjectMetadataExtractor")
def test_build_single_project(
    mock_project_metadata_extractor,
    mock_contribution_analyzer,
    mock_analyze_language_share,
    mock_detect_language_per_file,
):
    root, repo_folder = _make_folder_tree()
    builder = RepoProjectBuilder(root)

    repo_path = Path("/fake/extract/dir/MyRepo")

    # Mock Metadata Extractor 
    mock_metadata_extractor = MagicMock()
    mock_metadata_extractor.extract_metadata.return_value = {
        "project_metadata": {
            "total_files": 3,
            "start_date": "2025-01-01",
            "end_date": "2025-02-01",
        },
        "category_summary": {"counts": {"code": 3}},
    }
    mock_metadata_extractor.collect_all_files.return_value = [
        MagicMock(file_name="foo.py"),
        MagicMock(file_name="bar.py"),
    ]
    mock_project_metadata_extractor.return_value = mock_metadata_extractor

    # Mock Contribution Analyzer
    mock_contrib = MagicMock()
    mock_contrib.analyze.return_value = {
        "Alice": MagicMock(),
        "Bob": MagicMock(),
    }
    mock_contribution_analyzer.return_value = mock_contrib

    # inject into builder
    builder.contribution_analyzer = mock_contrib

    # Mock Language Detection
    mock_analyze_language_share.return_value = {"Python": 100.0}
    mock_detect_language_per_file.return_value = "Python"

    #ACT
    project = builder._build_single_project(repo_path)

    # ASSERT
    assert project is not None
    assert project.authors == ["Alice", "Bob"]


# testing that full scan() returns multiple projects

@patch("src.analyzers.RepoProjectBuilder.RepoFinder")
@patch("src.analyzers.RepoProjectBuilder.RepoProjectBuilder._build_single_project")
def test_scan_multiple_repos(mock_build_single, mock_finder):
    root, repoA, repoB = build_zip_tree()
    builder = RepoProjectBuilder(root)

    # Fake extracted repo paths
    mock_finder.return_value.find_repos.return_value = [
        Path("/extract/RepoA"),
        Path("/extract/RepoB"),
    ]

    # Make the builder return a simple dummy project each time
    mock_build_single.side_effect = ["ProjA", "ProjB"]

    projects = builder.scan(Path("/extract"))

    assert projects == ["ProjA", "ProjB"]
    assert mock_build_single.call_count == 2
