from pathlib import Path
from typing import Set, List, Dict, Any, Optional, Tuple

# Import GitPython for direct use within the analyzer.
from git import Repo, GitCommandError

from src.Project import Project
from src.ProjectManager import ProjectManager
from utils.RepoFinder import RepoFinder


class GitRepoAnalyzer:
    """
    Orchestrates the analysis and storage of Git repository projects.
    This class is the central component for the Git analysis workflow.
    """

    def __init__(self, repo_finder: RepoFinder, project_manager: ProjectManager):
        """
        Initializes the GitRepoAnalyzer with its dependencies.

        Args:
            repo_finder: An instance of RepoFinder to discover repository paths.
            project_manager: An instance of ProjectManager for database operations.
        """
        self._repo_finder = repo_finder
        self._project_manager = project_manager
        print("GitRepoAnalyzer initialized with dependencies.")

    def run_analysis_from_path(self, base_dir: Path) -> Tuple[List[Project], List[str]]:
        """
        Executes the full workflow: find, analyze, and persist projects.

        This method serves as the primary entry point. It uses the RepoFinder to
        get repository paths, analyzes each one, and uses "upsert" logic to save
        the resulting `Project` data object.

        Args:
            base_dir: The directory where to start searching for Git repositories.

        Returns:
            A tuple containing:
            - A list of the analyzed and persisted `Project` objects.
            - A list of all unique author names found across all repositories.
        """
        print(f"Starting analysis workflow from base directory: {base_dir}")
        repo_paths = self._repo_finder.find_repos(base_dir)
        analyzed_projects: List[Project] = []
        all_authors_across_repos: Set[str] = set()

        if not repo_paths:
            return analyzed_projects, []

        for repo_path in repo_paths:
            # The entire process for a single repo is encapsulated here.
            project_data, authors = self._analyze_and_prepare_project(repo_path)
            if project_data:
                self._project_manager.set(project_data)
                print(f"Successfully stored/updated project '{project_data.name}' in the database.")
                analyzed_projects.append(project_data)
                all_authors_across_repos.update(authors)

        return analyzed_projects, sorted(list(all_authors_across_repos))

    def _analyze_and_prepare_project(self, repo_path: Path) -> Tuple[Optional[Project], Set[str]]:
        """
        Analyzes a single repository and prepares the Project data object.

        Args:
            repo_path: The path to the root of the Git repository.

        Returns:
            A tuple containing:
            - An initialized and populated `Project` object, or None if analysis fails.
            - A set of author names found in the repository.
        """
        project_name = repo_path.name
        print(f"Analyzing repository for project: '{project_name}'")
        all_authors: Set[str] = set()

        try:
            # The Repo object is now created and managed here, within the analyzer.
            repo = Repo(repo_path)

            # Ref: commit.author.name provides the author's name as configured in git.
            # https://gitpython.readthedocs.io/en/stable/reference.html#git.objects.util.Actor
            for commit in repo.iter_commits():
                all_authors.add(commit.author.name)

            author_count = len(all_authors)
            status = "collaborative" if author_count > 1 else "individual"

            # Check for an existing project in the database.
            existing_project = self._project_manager.get_by_name(project_name)
            if existing_project:
                print(f"Found existing project '{project_name}'. Merging results.")
                # Use the existing project as a base to preserve its ID and other data.
                project = existing_project
                project.authors = sorted(list(all_authors))
                project.collaboration_status = status
                project.update_author_count()
            else:
                # Create a new, pure Project data object.
                project = Project(
                    name=project_name,
                    authors=sorted(list(all_authors)),
                    collaboration_status=status
                )
                project.update_author_count()

            return project, all_authors

        except (GitCommandError, Exception) as e:
            print(f"Error during analysis of '{project_name}': {e}")
            return None, set()
