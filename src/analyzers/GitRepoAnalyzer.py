from pathlib import Path
from typing import Set, List, Dict, Any, Optional

from src.Project import Project
from src.ProjectManager import ProjectManager
from utils.RepoFinder import RepoFinder


class GitRepoAnalyzer:
    """
    Orchestrates the analysis and storage of Git repository projects.
    This class is responsible for finding repositories, analyzing them,
    and persisting the results to the database.
    """

    def __init__(self, repo_finder: RepoFinder, project_manager: ProjectManager):
        """
        Initializes the GitRepoAnalyzer with its dependencies.

        Args:
            repo_finder: An instance of RepoFinder to discover repositories.
            project_manager: An instance of ProjectManager for database operations.
        """
        self._repo_finder = repo_finder
        self._project_manager = project_manager
        print("GitRepoAnalyzer initialized with dependencies.")

    def run_analysis_from_path(self, base_dir: Path) -> List[Project]:
        """
        Executes the full workflow: find, analyze, and persist projects.

        This method serves as the primary entry point for the analysis process.
        It uses the injected RepoFinder to discover projects, analyzes each one,
        and then uses an "upsert" logic to save the results via the ProjectManager.

        Args:
            base_dir: The directory where to start searching for Git repositories.

        Returns:
            A list of the analyzed and persisted Project objects.
        """
        print(f"Starting analysis workflow from base directory: {base_dir}")
        projects_found = self._repo_finder.find_repos(base_dir)
        analyzed_projects: List[Project] = []

        if not projects_found:
            print("No projects found to analyze.")
            return analyzed_projects

        for project in projects_found:
            # Perform the core analysis of the repository.
            analysis_data = self._analyze_repo(project)
            if not analysis_data:
                continue

            # Check if a project with the same name already exists in the database.
            existing_project = self._project_manager.get_by_name(project.name)
            if existing_project:
                print(f"Found existing project '{project.name}'. Merging results.")
                project.id = existing_project.id  # Preserve the original database ID.

            # Update the project object with the new analysis data.
            project.authors = analysis_data["authors"]
            project.collaboration_status = analysis_data["collaboration_status"]
            project.update_author_count()

            # Persist the final, enriched project object to the database.
            self._project_manager.set(project)
            print(f"Successfully stored/updated project '{project.name}' in the database.")
            analyzed_projects.append(project)

        return analyzed_projects

    def _analyze_repo(self, project: Project) -> Optional[Dict[str, Any]]:
        """
        Performs a repository-wide analysis for a single project.

        This private method contains the logic for iterating through commits to
        determine the unique authors and overall collaboration status.

        Args:
            project: The Project object to analyze.

        Returns:
            A dictionary with analysis results, or None if analysis fails.
        """
        if not project.repo:
            print(f"Skipping analysis for '{project.name}' due to missing repository object.")
            return None

        print(f"Analyzing repository for project: '{project.name}'")
        all_authors: Set[str] = set()

        try:
            # Ref: repo.iter_commits() provides an iterator for all commits.
            # https://gitpython.readthedocs.io/en/stable/reference.html#git.repo.base.Repo.iter_commits
            commits = list(project.repo.iter_commits())
            for commit in commits:
                all_authors.add(commit.author.email)
        except Exception as e:
            print(f"Error during commit analysis for '{project.name}': {e}")
            return None

        author_count = len(all_authors)
        status = "collaborative" if author_count > 1 else "individual"

        return {
            "authors": sorted(list(all_authors)),
            "collaboration_status": status
        }
