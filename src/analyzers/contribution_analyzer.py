from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Set, Any
from git import Repo, GitCommandError
import re

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
class AuthorIdentity:
    """Canonical identity keyed by email, with display name."""
    email: str
    display_name: str  # most recently seen name for this email
from src.FileCategorizer import FileCategorizer
import yaml

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
    
    def _load_mailmap(self, repo_path: str) -> Dict[str, str]:
        """
        Returns {raw_email: canonical_email} by parsing .mailmap.
        Falls back to empty dict if no .mailmap exists.
        """
        mailmap: Dict[str, str] = {}
        mailmap_path = Path(repo_path) / ".mailmap"
        if not mailmap_path.exists():
            return mailmap
        
        with open(mailmap_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # Match: Canonical Name <canonical@email> <other@email>
                emails = re.findall(r"<([^>]+)>", line)
                if len(emails) == 2:
                    canonical_email, raw_email = emails[0].lower(), emails[1].lower()
                    mailmap[raw_email] = canonical_email
                elif len(emails) == 1:
                    # Just a name mapping, email stays the same
                    pass
        return mailmap

    def _resolve_email(self, email: str, mailmap: Dict[str, str]) -> str:
        """Maps a raw email to its canonical form via mailmap."""
        return mailmap.get(email.lower().strip(), email.lower().strip())
    
    def _names_are_similar(self, a: str, b: str) -> bool:
        """Returns True if names share enough words to likely be the same person."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        shared = words_a & words_b
        return len(shared) >= 2

    def detect_and_write_mailmap(self, repo_path: str, author_map: Dict[str, str]) -> Dict[str, str]:
        """
        Detects likely duplicate contributors and prompts user to merge them.
        Writes a .mailmap file if merges are confirmed, and returns an updated author_map.
        Two heuristics:
        1. Same display name (case-insensitive), different emails
        2. One email is a GitHub no-reply and the name shares >= 2 words with another
        """
        mailmap_path = Path(repo_path) / ".mailmap"

        # Load existing mailmap entries so we don't re-prompt or duplicate them
        existing_entries: set[str] = set()
        if mailmap_path.exists():
            with open(mailmap_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        existing_entries.add(line)

        # --- Heuristic 1: same name, different emails ---
        name_to_emails: Dict[str, List[str]] = {}
        for email, name in author_map.items():
            key = name.lower().strip()
            name_to_emails.setdefault(key, []).append(email)

        duplicate_groups: List[List[str]] = [
            emails for emails in name_to_emails.values() if len(emails) > 1
        ]

        # --- Heuristic 2: noreply email where name shares >= 2 words with another name ---
        noreply_emails = [(e, n) for e, n in author_map.items() if "noreply.github.com" in e]
        personal_emails = [(e, n) for e, n in author_map.items() if "noreply.github.com" not in e]

        already_grouped = {e for group in duplicate_groups for e in group}

        for noreply_email, noreply_name in noreply_emails:
            if noreply_email in already_grouped:
                continue
            for personal_email, personal_name in personal_emails:
                if personal_email in already_grouped:
                    continue
                if self._names_are_similar(noreply_name, personal_name):
                    duplicate_groups.append([personal_email, noreply_email])
                    already_grouped.add(noreply_email)
                    already_grouped.add(personal_email)
                    break

        if not duplicate_groups:
            return author_map

        print("\nPossible duplicate contributors detected:")
        mailmap_entries: List[str] = []
        updated_map = dict(author_map)

        for emails in duplicate_groups:
            # Use the longest name as the canonical display name
            display_name = max((author_map[e] for e in emails), key=len)
            print(f"\n  '{display_name}' appears with multiple emails:")
            for i, email in enumerate(emails):
                print(f"    {i + 1}: {email} ({author_map[email]})")

            # Prefer non-noreply as canonical email
            canonical = next((e for e in emails if "noreply" not in e), emails[0])
            others = [e for e in emails if e != canonical]

            print(f"  Suggested canonical: {canonical}")
            try:
                confirm = input("  Merge these into one? (y/n): ").strip().lower()
            except KeyboardInterrupt:
                print("\nSkipping merge.")
                continue

            if confirm == "y":
                for raw_email in others:
                    entry = f"{display_name} <{canonical}> <{raw_email}>"
                    if entry not in existing_entries:
                        mailmap_entries.append(entry)
                    updated_map.pop(raw_email, None)
                    # Update canonical entry to use the longest name
                    if canonical in updated_map:
                        updated_map[canonical] = display_name

        if mailmap_entries:
            with open(mailmap_path, "a", encoding="utf-8") as f:
                if not existing_entries:
                    f.write("# Auto-generated by Project Analyzer\n")
                f.write("\n".join(mailmap_entries) + "\n")
            print(f"\n.mailmap updated at {mailmap_path}")
            print("Future runs will automatically apply these merges.")

        return updated_map

    def get_all_authors(self, repo_path: str) -> Dict[str, str]:
        try:
            repo = Repo(repo_path)
            mailmap = self._load_mailmap(repo_path)
            author_map: Dict[str, str] = {}
            for commit in repo.iter_commits():
                if commit.author and commit.author.email:
                    email = self._resolve_email(commit.author.email, mailmap)
                    if email not in author_map:
                        author_map[email] = commit.author.name
            return author_map
        except (GitCommandError, ValueError) as e:
            print(f"  - Warning: Could not read Git authors from '{repo_path}'. Error: {e}")
            return {}

    def analyze(self, repo_path: str) -> Dict[str, ContributionStats]:
        try:
            repo = Repo(repo_path)
            mailmap = self._load_mailmap(repo_path)
            author_stats: Dict[str, ContributionStats] = {}

            for commit in repo.iter_commits():
                if not commit.author or not commit.author.email:
                    continue
                email = self._resolve_email(commit.author.email, mailmap)

                if email not in author_stats:
                    author_stats[email] = ContributionStats()
                stats = author_stats[email]
                stats.total_commits += 1

                try:
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
            print(f"  - Warning: Could not analyze contributions for '{repo_path}'. Error: {e}")
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
