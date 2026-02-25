from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Set, Any
from git import Repo, GitCommandError
from src.FileCategorizer import FileCategorizer
import yaml


CONFIG_DIR = Path(__file__).parent.parent / "config"
ROLE_SIGNALS_FILE = CONFIG_DIR / "role_signals.yml"

class RoleSignals:
    def __init__(self):
        with open(ROLE_SIGNALS_FILE, "r", encoding="utf-8") as f:
            self.conf = (yaml.safe_load(f) or {}).get("roles", {})
    
    def infer_role_bucket(self, path: str, language: str, category: str) -> str:
        path_l = path.lower()
        lang = (language or "").strip()
        cat = (category or "").strip()

        best_role = "none"
        best_score = 0

        for role, rules in self.conf.items():
            score = 0

            # categories
            if cat and cat in set(rules.get("categories", [])):
                score += 2

            # languages
            if lang and lang in set(rules.get("languages", [])):
                score += 2

            # path patterns
            for p in rules.get("path_patterns", []):
                if p.lower() in path_l:
                    score += 1

            if score > best_score:
                best_score = score
                best_role = role

        # Require at least some evidence
        return best_role if best_score >= 2 else "none"

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

    contribution_by_type: Dict[str, int] = field(default_factory=lambda: {
        "code": 0,
        "docs": 0,
        "test": 0,
        "other": 0
    })

    contribution_by_category: Dict[str, int] = field(default_factory=dict)
    contribution_by_language: Dict[str, int] = field(default_factory=dict)
    contribution_by_role_signal: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Serializes the dataclass to a dictionary, converting set to list."""
        data = self.__dict__.copy()
        data["files_touched"] = sorted(list(self.files_touched))
        return data

class ContributionAnalyzer:
    """
    Analyzes all author contributions in a Git repository.
    """
    def _normalize_author_identity(self, name: str | None, email: str | None) -> str | None:
        normalized_name = (name or "").strip()
        normalized_email = (email or "").strip().lower()

        if normalized_name:
            return " ".join(normalized_name.split())

        if normalized_email and "@" in normalized_email:
            return normalized_email.split("@", 1)[0]

        return None
    

    def __init__(self):
        self.file_categorizer = FileCategorizer()
        self.role_signals = RoleSignals()

    def _language_from_extension(self, path: str) -> str:
        ext = Path(path).suffix.lstrip(".").lower()
        return self.file_categorizer.language_map.get(ext, "")

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
        Scans a repository to get a unique list of all contributor identities.
        This is a lightweight operation focused solely on retrieving contributors.
        """
        try:
            repo = Repo(repo_path)
            author_names: Dict[str, str] = {}
            for commit in repo.iter_commits():
                for identity in [getattr(commit, "author", None), getattr(commit, "committer", None)]:
                    if not identity:
                        continue
                    normalized = self._normalize_author_identity(
                        getattr(identity, "name", None),
                        getattr(identity, "email", None),
                    )
                    if not normalized:
                        continue

                    identity_key = normalized.casefold()
                    current = author_names.get(identity_key)
                    if current is None or (current.islower() and any(ch.isupper() for ch in normalized)):
                        author_names[identity_key] = normalized

            return sorted(list(author_names.values()), key=lambda n: n.lower())
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
                author_name = self._normalize_author_identity(
                    getattr(commit.author, "name", None),
                    getattr(commit.author, "email", None),
                )
                if not author_name:
                    continue

                if author_name not in author_stats:
                    author_stats[author_name] = ContributionStats()

                stats = author_stats[author_name]
                stats.total_commits += 1

                try:
                    # This is the standard, most efficient way to get stats
                    commit_stats = commit.stats.files
                    for file_path, file_stat_values in commit_stats.items():
                        lines_changed = file_stat_values['insertions'] + file_stat_values['deletions']
                        
                        # YAML driven category for role inference
                        lang = self._language_from_extension(file_path)
                        yaml_cat = self.file_categorizer.classify_file({
                            "path": file_path,
                            "language": lang
                        })
                        if yaml_cat == "ignored":
                            continue

                        stats.lines_added += file_stat_values['insertions']
                        stats.lines_deleted += file_stat_values['deletions']
                        stats.files_touched.add(file_path)

                        coarse_type = self._categorize_file_path(file_path)
                        stats.contribution_by_type[coarse_type] = (
                            stats.contribution_by_type.get(coarse_type, 0) + lines_changed
                        )

                        if lang:
                            stats.contribution_by_language[lang] = (
                                stats.contribution_by_language.get(lang, 0) + lines_changed
                            )
                        stats.contribution_by_category[yaml_cat] = (
                            stats.contribution_by_category.get(yaml_cat, 0) + lines_changed
                            )
                        
                        role_bucket = self.role_signals.infer_role_bucket(file_path, lang, yaml_cat)
                        if role_bucket != "none":
                            stats.contribution_by_role_signal[role_bucket] = (
                                stats.contribution_by_role_signal.get(role_bucket, 0) + lines_changed
                            )

                except (GitCommandError, ValueError) as e:
                    # This block catches errors from `commit.stats`, which can happen if a parent is missing
                    # (e.g., in a shallow clone) or for the very first commit.

                    # Check if it's the initial commit (no parents)
                    if not commit.parents:
                        for blob in commit.tree.traverse():
                            if blob.type == 'blob':
                                try:
                                    lines = blob.data_stream.read().decode(errors='ignore').count('\n') + 1

                                    lang = self._language_from_extension(blob.path)
                                
                                    yaml_cat = self.file_categorizer.classify_file({
                                        "path": blob.path,
                                        "language": lang
                                    })
                                    if yaml_cat == "ignored":
                                        continue

                                    stats.lines_added += lines
                                    stats.files_touched.add(blob.path)

                                    coarse_type = self._categorize_file_path(blob.path)
                                    stats.contribution_by_type[coarse_type] = (
                                        stats.contribution_by_type.get(coarse_type, 0) + lines
                                    )

                                    if lang:
                                        stats.contribution_by_language[lang] = (
                                            stats.contribution_by_language.get(lang, 0) + lines
                                        )
                                    stats.contribution_by_category[yaml_cat] = (
                                        stats.contribution_by_category.get(yaml_cat, 0) + lines
                                        )
                                    
                                    role_bucket = self.role_signals.infer_role_bucket(blob.path, lang, yaml_cat)
                                    if role_bucket != "none":
                                        stats.contribution_by_role_signal[role_bucket] = (
                                            stats.contribution_by_role_signal.get(role_bucket, 0) + lines
                                        )
                                    
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
