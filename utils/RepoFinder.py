import os
from pathlib import Path
from typing import List

# Directly uses the existing Project model, eliminating the need for a transitional class.
from src.Project import Project


class RepoFinder:
    """
    Utility class to discover Git repositories within a given directory structure.
    """

    def find_repos(self, base_dir: Path) -> List[Project]:
        """
        Recursively finds all Git repositories and instantiates Project objects for them.

        This method traverses the directory tree from the `base_dir`. Upon finding a
        `.git` directory, it assumes the parent directory is the root of a project.
        It then creates an instance of the main `Project` model. To avoid analyzing
        Git submodules as distinct projects, the traversal depth is pruned once a
        repository is found.

        Ref: The `os.walk` function allows for in-place modification of the `dirs` list
        to control the traversal path. See https://docs.python.org/3/library/os.html#os.walk.

        Args:
            base_dir: The starting directory for the repository search.

        Returns:
            A list of `Project` objects, initialized with their name and repository path.
        """
        projects: List[Project] = []
        print(f"Searching for Git repositories in: {base_dir}")

        for root, dirs, _ in os.walk(base_dir):
            if "__MACOSX" in root:
                continue

            if ".git" in dirs:
                repo_path = Path(root)
                project_name = repo_path.name
                print(f"Found Git repository for project: {project_name}")

                # Instantiate the primary Project model with runtime-specific data.
                project = Project(name=project_name, repo_path=repo_path)
                projects.append(project)

                # Prune the directory search to prevent descending into submodules.
                dirs.clear()

        if not projects:
            print("No Git repositories were found in the specified path.")

        return projects
