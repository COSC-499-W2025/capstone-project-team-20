from pathlib import Path
from unittest.mock import MagicMock, patch

from src.analyzers.RepoProjectBuilder import RepoProjectBuilder
from src.models.Project import Project
from src.ProjectFolder import ProjectFolder

def build_zip_tree():
    repoA = MagicMock(spec=ProjectFolder)
    repoA.name = "RepoA/"
    repoB = MagicMock(spec=ProjectFolder)
    repoB.name = "RepoB/"
    return [repoA, repoB], repoA, repoB

def test_build_single_project_minimal():
    roots, repoA, repoB = build_zip_tree()
    builder = RepoProjectBuilder(roots)
    repo_path = Path("/fake/extract/dir/RepoA")

    project = builder._build_single_project(repo_path)

    assert isinstance(project, Project)
    assert project.name == "RepoA"
    # FIX: Assert against the correct folder name with a trailing slash
    assert project.root_folder == "RepoA/"
