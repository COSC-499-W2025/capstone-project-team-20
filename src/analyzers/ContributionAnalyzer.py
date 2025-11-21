from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Set, Tuple
from git import Repo, Commit

@dataclass
class ContributionStats:
    """
    A data container for aggregated contribution statistics.
    Can be used for a single user, a group of users, or an entire project.
    """
    total_commits: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    files_touched: Set[str] = field(default_factory=set)
    contribution_by_type: Dict[str, int] = field(default_factory=lambda: {"code": 0, "docs": 0, "test": 0})

    def to_dict(self) -> Dict:
        """Serializes the dataclass to a dictionary, converting set to list."""
        data = self.__dict__.copy()
        data["files_touched"] = sorted(list(self.files_touched))
        return data

class ContributionAnalyzer:
    """
    Analyzes and aggregates the contributions of authors in a Git repository.
    """
    def _categorize_file_path(self, path: str) -> str:
        """Categorizes a file path into 'code', 'docs', or 'test'."""
        p = Path(path.lower())
        if "test" in p.parts:
            return "test"
        if "doc" in p.parts or "docs" in p.parts:
            return "docs"
        return "code"

    def analyze(self, repo_path: str, selected_author_names: List[str]) -> Tuple[ContributionStats, ContributionStats]:
        """
        Crawls a Git repository to produce aggregated contribution statistics.

        This method iterates through all commits to calculate two sets of stats:
        1. Aggregated stats for the `selected_author_names`.
        2. Aggregated stats for the entire project (all authors).

        Args:
            repo_path: The file system path to the Git repository.
            selected_author_names: A list of author names to aggregate for the primary analysis.

        Returns:
            A tuple containing two ContributionStats objects:
            (stats_for_selected_authors, stats_for_total_project)
        """
        repo = Repo(repo_path)
        selected_stats = ContributionStats()
        total_stats = ContributionStats()

        for commit in repo.iter_commits():
            author_name = commit.author.name

            # Aggregate stats for the entire project in every iteration
            total_stats.total_commits += 1
            commit_stats = commit.stats.files
            for file_path, file_stats in commit_stats.items():
                lines_changed = file_stats['insertions'] + file_stats['deletions']
                total_stats.lines_added += file_stats['insertions']
                total_stats.lines_deleted += file_stats['deletions']
                total_stats.files_touched.add(file_path)
                category = self._categorize_file_path(file_path)
                total_stats.contribution_by_type[category] += lines_changed

            # If the author is in the selected list, aggregate their stats separately
            if author_name in selected_author_names:
                selected_stats.total_commits += 1
                for file_path, file_stats in commit_stats.items():
                    lines_changed = file_stats['insertions'] + file_stats['deletions']
                    selected_stats.lines_added += file_stats['insertions']
                    selected_stats.lines_deleted += file_stats['deletions']
                    selected_stats.files_touched.add(file_path)
                    category = self._categorize_file_path(file_path)
                    selected_stats.contribution_by_type[category] += lines_changed

        return selected_stats, total_stats
