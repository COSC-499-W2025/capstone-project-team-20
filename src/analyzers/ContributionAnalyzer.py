from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Set, Tuple
from git import Repo

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
    contribution_by_type: Dict[str, int] = field(default_factory=lambda: {"code": 0, "docs": 0, "test": 0})

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
        # Check for both singular and plural forms
        if "test" in p.parts or "tests" in p.parts:
            return "test"
        if "doc" in p.parts or "docs" in p.parts:
            return "docs"
        return "code"

    def get_all_authors(self, repo_path: str) -> List[str]:
        """
        Scans a repository to get a unique list of all author names.
        This is a lightweight operation focused solely on retrieving contributors.
        """
        repo = Repo(repo_path)
        author_names: Set[str] = set()
        for commit in repo.iter_commits():
            author_names.add(commit.author.name)
        return sorted(list(author_names))

    def analyze(self, repo_path: str) -> Dict[str, ContributionStats]:
        """
        Performs a comprehensive analysis of a Git repository, calculating
        detailed contribution statistics for every author in a single pass.

        Args:
            repo_path: The file system path to the Git repository.

        Returns:
            A dictionary mapping each author's name to their ContributionStats object.
        """
        repo = Repo(repo_path)
        author_stats: Dict[str, ContributionStats] = {}

        for commit in repo.iter_commits():
            author_name = commit.author.name

            # Get or create the stats object for the commit author.
            if author_name not in author_stats:
                author_stats[author_name] = ContributionStats()

            stats = author_stats[author_name]
            stats.total_commits += 1

            commit_stats = commit.stats.files
            for file_path, file_stat_values in commit_stats.items():
                lines_changed = file_stat_values['insertions'] + file_stat_values['deletions']
                stats.lines_added += file_stat_values['insertions']
                stats.lines_deleted += file_stat_values['deletions']
                stats.files_touched.add(file_path)

                category = self._categorize_file_path(file_path)
                stats.contribution_by_type[category] += lines_changed

        return author_stats

    def calculate_share(self, selected_stats: ContributionStats, total_stats: ContributionStats) -> List[str]:
        """
        Given stats for a selected user and the total project, calculates the
        contribution share and returns a formatted list of strings.
        """
        total_lines_edited_project = total_stats.lines_added + total_stats.lines_deleted
        total_lines_edited_selected = selected_stats.lines_added + selected_stats.lines_deleted
        project_share = (total_lines_edited_selected / total_lines_edited_project) * 100 if total_lines_edited_project > 0 else 0

        return [
            f"Total Commits: {selected_stats.total_commits}",
            f"Lines Added: {selected_stats.lines_added}",
            f"Lines Deleted: {selected_stats.lines_deleted}",
            f"Contribution Share: {project_share:.2f}%"
        ]
