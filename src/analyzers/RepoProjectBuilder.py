from pathlib import Path
from typing import List
from src.models.Project import Project
from src.ProjectFolder import ProjectFolder
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.ContributionAnalyzer import ContributionAnalyzer
from utils.RepoFinder import RepoFinder
import io
import contextlib

class RepoProjectBuilder:
    """
    Scans an extracted directory for Git repositories or top-level folders,
    maps them to the ZIP's internal folder tree, and builds fully populated Project objects.
    """

    def __init__(self, root_folders: List[ProjectFolder]):
        """
        root_folders: A list of ProjectFolder roots created by parsing the ZIP.
        """
        self.root_folders = root_folders
        self.repo_finder = RepoFinder()
        self.contribution_analyzer = ContributionAnalyzer()

    def scan(self, extract_dir: Path) -> List[Project]:
        """
        Main entry point. Scans for Git repos, and for non-repo folders,
        creates a project for each root folder.
        Returns a list of Project objects.
        """
        repo_paths = self.repo_finder.find_repos(extract_dir)
        projects = []

        processed_repo_names = set()

        # First, process all found Git repositories
        for repo_path in repo_paths:
            proj = self._build_single_project(repo_path)
            if proj:
                projects.append(proj)
                processed_repo_names.add(proj.name.lower())

        # Then, process root folders that were NOT identified as Git repos
        for root_folder in self.root_folders:
            folder_name = root_folder.name.strip('/')
            if folder_name.lower() not in processed_repo_names:
                # This folder is not a git repo, create a basic project for it
                proj = Project(
                    name=folder_name,
                    file_path=str(extract_dir / folder_name),
                    root_folder=root_folder.name
                )
                projects.append(proj)

        return projects

    def suppress_output(self):
        """Silence stdout while running noisy extractors."""
        return contextlib.redirect_stdout(io.StringIO())

    def _build_single_project(self, repo_path: Path) -> Project:
        """Build and return an empty project object for a found repository."""
        repo_name = repo_path.name
        folder = self._find_folder_by_name(repo_name)
        if not folder:
            print(f"[WARN] Could not map repo folder '{repo_name}' inside ZIP.")
            # Create a project even if mapping fails
            return Project(
                name=repo_name,
                file_path=str(repo_path),
                root_folder=repo_name # Fallback
            )

        return Project(
            name=repo_name,
            file_path=str(repo_path),
            root_folder=str(folder.name)
        )

    def _find_folder_by_name(self, target_name: str) -> ProjectFolder | None:
        """
        Search through the root folders to find one matching the target name.
        """
        for folder in self.root_folders:
            # Name comparison should be case-insensitive and ignore trailing slashes
            if folder.name.strip('/').lower() == target_name.lower():
                return folder
        return None
