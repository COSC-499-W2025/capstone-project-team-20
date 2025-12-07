from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Set, Any
from git import Repo, GitCommandError

@dataclass
class ContributionStats:
    """
    A data container for contribution statistics. Can be used for an individual
    author or aggregated for a group or an entire project.
    """
    lines_added: int = 0
    lines_deleted: int = 0
    total_commits: int = 0
    files_touched: Set[str] = field(default_factory=set)
    contribution_by_type: Dict[str, int] = field(default_factory=lambda: {"code": 0, "docs": 0, "test": 0, "other": 0})

    def to_dict(self) -> Dict:
        """Serializes the dataclass to a dictionary, converting set to list."""
        data = self.__dict__.copy()
        data["files_touched"] = sorted(list(self.files_touched))
        return data

class ContributionAnalyzer:
    """
    Analyzes all author contributions in a Git repository.
    """
    def _categorize_file_path(self, path: str) -> str:
        """Categorizes a file path into 'code', 'docs', or 'test'."""
        p = Path(path.lower())
        if "test" in p.parts or "tests" in p.parts:
            return "test"
        if "doc" in p.parts or "docs" in p.parts:
            return "docs"
        if any(p.name.endswith(ext) for ext in ['.py', '.js', '.java', '.c', '.cpp', '.go', '.rs']):
            return "code"
        return "other"

    def get_all_authors(self, repo_path: str) -> List[str]:
        """
        Scans a repository to get a unique list of all author names.
        This is a lightweight operation focused solely on retrieving contributors.
        """
        try:
            repo = Repo(repo_path)
            author_names: Set[str] = set()
            for commit in repo.iter_commits():
                if commit.author:
                    author_names.add(commit.author.name)
            return sorted(list(author_names))
        except (GitCommandError, ValueError) as e:
            print(f"  - Warning: Could not read Git authors from '{repo_path}'. Error: {e}")
            return []

    def analyze(self, repo_path: str) -> Dict[str, ContributionStats]:
        """
        Performs a comprehensive analysis of a Git repository, calculating
        detailed contribution statistics for every author in a single pass.
        This version is robust against shallow clones and initial commits.
        """
        try:
            repo = Repo(repo_path)
            author_stats: Dict[str, ContributionStats] = {}

            for commit in repo.iter_commits():
                if not commit.author: continue
                author_name = commit.author.name

                if author_name not in author_stats:
                    author_stats[author_name] = ContributionStats()
                stats = author_stats[author_name]
                stats.total_commits += 1

                try:
                    # This is the standard, most efficient way to get stats
                    commit_stats = commit.stats.files
                    for file_path, file_stat_values in commit_stats.items():
                        lines_changed = file_stat_values['insertions'] + file_stat_values['deletions']
                        stats.lines_added += file_stat_values['insertions']
                        stats.lines_deleted += file_stat_values['deletions']
                        stats.files_touched.add(file_path)
                        category = self._categorize_file_path(file_path)
                        stats.contribution_by_type[category] += lines_changed

                except (GitCommandError, ValueError) as e:
                    # This block catches errors from `commit.stats`, which can happen if a parent is missing
                    # (e.g., in a shallow clone) or for the very first commit.

                    # Check if it's the initial commit (no parents)
                    if not commit.parents:
                        for blob in commit.tree.traverse():
                            if blob.type == 'blob':
                                try:
                                    lines = blob.data_stream.read().decode(errors='ignore').count('\n') + 1
                                    stats.lines_added += lines
                                    stats.files_touched.add(blob.path)
                                    category = self._categorize_file_path(blob.path)
                                    stats.contribution_by_type[category] += lines
                                except Exception:
                                    pass # Ignore files that can't be decoded
                    # If it has parents but still failed, it's likely a shallow clone boundary.
                    # We can log this but continue, as we can't analyze what we don't have.
                    else:
                        print(f"  - Note: Could not get stats for commit {commit.hexsha[:7]} (likely shallow clone). Skipping stat count for this commit.")

            return author_stats
        except (GitCommandError, ValueError) as e:
            print(f"  - Warning: Could not analyze contributions for '{repo_path}'. It might be a corrupted or empty repository. Error: {e}")
            return {}

    def calculate_share(self, selected_stats: ContributionStats, total_stats: ContributionStats) -> Dict[str, Any]:
        """
        Given stats for a selected user and the total project, calculates the
        contribution share and returns it as a dictionary.
        """
        total_lines_edited_project = total_stats.lines_added + total_stats.lines_deleted
        total_lines_edited_selected = selected_stats.lines_added + selected_stats.lines_deleted
        project_share = (total_lines_edited_selected / total_lines_edited_project) * 100 if total_lines_edited_project > 0 else 0

        return {
            "total_commits": selected_stats.total_commits,
            "lines_added": selected_stats.lines_added,
            "lines_deleted": selected_stats.lines_deleted,
            "contribution_share_percent": round(project_share, 2)
        }
