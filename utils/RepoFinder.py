import os
from pathlib import Path
from typing import List

class RepoFinder:
    """
    A utility class to discover Git repositories within a given directory structure.
    Its sole responsibility is to identify repository paths.
    """

    def find_repos(self, base_dir: Path) -> List[Path]:
        """
        Recursively finds all Git repository paths within a given base directory.

        This method traverses the directory tree. When a `.git` directory is found,
        it records the path to its parent directory (the repository root). The traversal
        is then pruned to prevent descending into submodules.

        Ref: `os.walk` allows for in-place modification of the `dirs` list to control
        the traversal path. See: https://docs.python.org/3/library/os.html#os.walk

        Args:
            base_dir: The starting directory for the repository search.

        Returns:
            A list of `pathlib.Path` objects, each pointing to the root of a Git repository.
        """
        repo_paths: List[Path] = []
        print(f"Searching for Git repositories in: {base_dir}")

        if not base_dir.is_dir():
            print(f"Error: Provided path '{base_dir}' is not a directory.")
            return repo_paths

        for root, dirs, _ in os.walk(base_dir):
            if "__MACOSX" in root:
                continue

            if ".git" in dirs:
                repo_path = Path(root)
                print(f"Found Git repository at: {repo_path}")
                repo_paths.append(repo_path)

                # Prune the directory search to prevent descending into submodules.
                dirs.clear()

        if not repo_paths:
            print("No Git repositories were found in the specified path.")

        return repo_paths
