from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Set, Any, Tuple
from git import Repo, GitCommandError
import subprocess
import re

CONFIG_DIR = Path(__file__).parent.parent / "config"
ROLE_SIGNALS_FILE = CONFIG_DIR / "role_signals.yml"


class RoleSignals:
    def __init__(self):
        with open(ROLE_SIGNALS_FILE, "r", encoding="utf-8") as f:
            self.conf = (yaml.safe_load(f) or {}).get("roles", {})

        # Pre-built lookup tables for O(1) scoring instead of per-call loops
        self._lang_to_roles: Dict[str, List[str]] = {}
        self._cat_to_roles: Dict[str, List[str]] = {}
        self._path_patterns: List[tuple] = []  # [(pattern_lower, role)]

        for role, rules in self.conf.items():
            for lang in rules.get("languages", []):
                self._lang_to_roles.setdefault(lang, []).append(role)
            for cat in rules.get("categories", []):
                self._cat_to_roles.setdefault(cat, []).append(role)
            for p in rules.get("path_patterns", []):
                self._path_patterns.append((p.lower(), role))


    def infer_role_bucket(self, path: str, language: str, category: str) -> str:
        lang = (language or "").strip()
        cat = (category or "").strip()
        path_l = path.lower()
        scores: Dict[str, int] = {}
        if cat:
            for role in self._cat_to_roles.get(cat, []):
                scores[role] = scores.get(role, 0) + 2
        if lang:
            for role in self._lang_to_roles.get(lang, []):
                scores[role] = scores.get(role, 0) + 2
        for pattern, role in self._path_patterns:
            if pattern in path_l:
                scores[role] = scores.get(role, 0) + 1
        if not scores:
            return "none"
        best_role = max(scores, key=lambda r: scores[r])
        return best_role if scores[best_role] >= 2 else "none"

@dataclass
class AuthorIdentity:
    """Canonical identity keyed by email, with display name."""
    email: str
    display_name: str


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
        "code": 0, "docs": 0, "test": 0, "other": 0
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
    """Analyzes all author contributions in a Git repository."""

    def __init__(self):
        self.file_categorizer = FileCategorizer()
        self.role_signals = RoleSignals()
        # Memoised per-path classification caches.
        self._lang_cache: Dict[str, str] = {}
        self._cat_cache: Dict[str, str] = {}
        self._coarse_cache: Dict[str, str] = {}
        self._role_cache: Dict[Tuple[str, str, str], str] = {}

    # ------------------------------------------------------------------
    # Cached per-path helpers
    # ------------------------------------------------------------------

    def _language_from_extension(self, path: str) -> str:
        dot = path.rfind(".")
        ext = path[dot + 1:].lower() if dot != -1 and dot > path.rfind("/") else ""
        if ext not in self._lang_cache:
            self._lang_cache[ext] = self.file_categorizer.language_map.get(ext, "")
        return self._lang_cache[ext]

    def _classify_file(self, path: str, lang: str) -> str:
        if path not in self._cat_cache:
            self._cat_cache[path] = self.file_categorizer.classify_file(
                {"path": path, "language": lang}
            )
        return self._cat_cache[path]

    def _categorize_file_path(self, path: str) -> str:
        if path not in self._coarse_cache:
            lower = path.lower().replace("\\", "/")
            parts = lower.split("/")
            parts_set = set(parts)
            name = parts[-1] if parts else ""
            if "test" in parts_set or "tests" in parts_set:
                result = "test"
            elif "doc" in parts_set or "docs" in parts_set:
                result = "docs"
            elif any(name.endswith(ext) for ext in ['.py', '.js', '.java', '.c', '.cpp', '.go', '.rs']):
                result = "code"
            else:
                result = "other"
            self._coarse_cache[path] = result
        return self._coarse_cache[path]

    def _infer_role(self, path: str, lang: str, cat: str) -> str:
        key = (path, lang, cat)
        if key not in self._role_cache:
            self._role_cache[key] = self.role_signals.infer_role_bucket(path, lang, cat)
        return self._role_cache[key]

    def _classify_path(self, path: str) -> Tuple[str, str, str, str]:
        """Returns (lang, yaml_cat, coarse_type, role_bucket) for a file path."""
        lang = self._language_from_extension(path)
        yaml_cat = self._classify_file(path, lang)
        coarse_type = self._categorize_file_path(path)
        role_bucket = self._infer_role(path, lang, yaml_cat)
        return lang, yaml_cat, coarse_type, role_bucket

    # ------------------------------------------------------------------
    # Core: single-pass bulk log parser
    # ------------------------------------------------------------------

    def _parse_log_numstat(self, repo_path: str, mailmap: Dict[str, str]) -> Dict[str, Any]:
        """
        Run ONE `git log --numstat` subprocess and parse the entire history.

        This replaces per-commit GitPython calls (which each shell out to git
        individually). A single subprocess call with --numstat returns insertions,
        deletions, and filename for every file in every commit, which we stream-
        parse in O(lines) Python.

        Output format we parse:
            COMMIT <hash> <email> <name...>
            <ins>\t<del>\t<path>        (repeated per file; "-" for binary)
            <blank line>                (commit separator)

        Returns:
            Dict keyed by canonical email -> {
                "name": str,
                "commits": [ {"is_initial": bool, "files": {path: (ins, del)}} ]
            }
        """
        cmd = [
            "git", "-C", repo_path,
            "log",
            "--format=COMMIT %H %ae %aN",   # sentinel line per commit
            "--numstat",                      # ins/del/path lines follow
            "--diff-filter=ACDMRT",           # skip untracked/broken symlinks
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            raise RuntimeError("git executable not found on PATH")

        if result.returncode != 0:
            raise GitCommandError("git log", result.returncode, result.stderr)

        # Parse into per-author buckets directly -- no intermediate data structure.
        author_data: Dict[str, Dict] = {}
        current_email: str | None = None
        current_files: Dict[str, Tuple[int, int]] = {}
        is_first_commit_seen: Dict[str, bool] = {}  # sha -> True once

        # We need to know which commits are initial (no parents) to handle
        # them specially. git log --numstat already gives us the right diff
        # for the initial commit (it diffs against empty tree), so we actually
        # don't need to special-case it at all -- unlike GitPython which fails
        # on commit.stats for parentless commits.

        def _flush(email: str, files: Dict[str, Tuple[int, int]]) -> None:
            if email is None:
                return
            entry = author_data[email]
            entry["total_commits"] += 1
            entry["stats"].total_commits += 1  # add this line
            for path, (ins, dels) in files.items():
                self._accumulate_file(entry["stats"], path, ins, dels)

        for line in result.stdout.splitlines():
            if line.startswith("COMMIT "):
                # Flush previous commit
                if current_email is not None:
                    _flush(current_email, current_files)
                current_files = {}

                # Parse: "COMMIT <hash> <email> <name...>"
                parts = line.split(" ", 3)
                if len(parts) < 3:
                    current_email = None
                    continue
                raw_email = parts[2].strip()
                name = parts[3].strip() if len(parts) > 3 else raw_email
                canonical_email = mailmap.get(raw_email.lower(), raw_email.lower())

                if canonical_email not in author_data:
                    author_data[canonical_email] = {
                        "name": name,
                        "total_commits": 0,
                        "stats": ContributionStats(),
                    }
                current_email = canonical_email

            elif line == "" or current_email is None:
                continue

            else:
                # numstat line: "<ins>\t<del>\t<path>"
                # Binary files show "-\t-\t<path>" -- skip them.
                parts = line.split("\t", 2)
                if len(parts) == 3 and parts[0] != "-":
                    try:
                        ins = int(parts[0])
                        dels = int(parts[1])
                        path = parts[2].strip()
                        current_files[path] = (
                            current_files.get(path, (0, 0))[0] + ins,
                            current_files.get(path, (0, 0))[1] + dels,
                        )
                    except ValueError:
                        pass

        # Flush last commit
        if current_email is not None:
            _flush(current_email, current_files)

        return author_data

    def _accumulate_file(
        self, stats: ContributionStats, path: str, insertions: int, deletions: int
    ) -> None:
        """Apply one file's ins/del to a ContributionStats object."""
        lang, yaml_cat, coarse_type, role_bucket = self._classify_path(path)
        if yaml_cat == "ignored":
            return

        lines_changed = insertions + deletions
        stats.lines_added += insertions
        stats.lines_deleted += deletions
        stats.files_touched.add(path)

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
        if role_bucket != "none":
            stats.contribution_by_role_signal[role_bucket] = (
                stats.contribution_by_role_signal.get(role_bucket, 0) + lines_changed
            )

    # ------------------------------------------------------------------
    # Mailmap helpers
    # ------------------------------------------------------------------

    def _normalize_author_identity(self, name: str | None, email: str | None) -> str | None:
        normalized_name = (name or "").strip()
        normalized_email = (email or "").strip().lower()
        if normalized_name:
            return " ".join(normalized_name.split())
        if normalized_email and "@" in normalized_email:
            return normalized_email.split("@", 1)[0]
        return None

    def _load_mailmap(self, repo_path: str, config_manager=None) -> Dict[str, str]:
        mailmap: Dict[str, str] = {}
        mailmap_path = Path(repo_path) / ".mailmap"
        if config_manager:
            persisted = config_manager.get("mailmap_entries") or []
            if persisted:
                with open(mailmap_path, "a", encoding="utf-8") as f:
                    f.write("\n".join(persisted) + "\n")
        if not mailmap_path.exists():
            return mailmap
        with open(mailmap_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                emails = re.findall(r"<([^>]+)>", line)
                if len(emails) == 2:
                    canonical_email, raw_email = emails[0].lower(), emails[1].lower()
                    mailmap[raw_email] = canonical_email
        return mailmap

    def _resolve_email(self, email: str, mailmap: Dict[str, str]) -> str:
        return mailmap.get(email.lower().strip(), email.lower().strip())

    def _names_are_similar(self, a: str, b: str) -> bool:
        """Returns True if names share enough words to likely be the same person."""
        return len(set(a.lower().split()) & set(b.lower().split())) >= 2

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_and_write_mailmap(
        self, repo_path: str, author_map: Dict[str, str], config_manager=None
    ) -> Dict[str, str]:
        mailmap_path = Path(repo_path) / ".mailmap"
        existing_entries: set[str] = set()
        if mailmap_path.exists():
            with open(mailmap_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        existing_entries.add(line)

        name_to_emails: Dict[str, List[str]] = {}
        for email, name in author_map.items():
            name_to_emails.setdefault(name.lower().strip(), []).append(email)

        duplicate_groups: List[List[str]] = [
            emails for emails in name_to_emails.values() if len(emails) > 1
        ]

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
                    already_grouped.update([noreply_email, personal_email])
                    break

        if not duplicate_groups:
            return author_map

        print("\nPossible duplicate contributors detected:")
        mailmap_entries: List[str] = []
        updated_map = dict(author_map)

        for emails in duplicate_groups:
            display_name = max((author_map[e] for e in emails), key=len)
            print(f"\n  '{display_name}' appears with multiple emails:")
            for i, email in enumerate(emails):
                print(f"    {i + 1}: {email} ({author_map[email]})")
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
                    updated_map[canonical] = display_name

        if mailmap_entries:
            with open(mailmap_path, "a", encoding="utf-8") as f:
                if not existing_entries:
                    f.write("# Auto-generated by Project Analyzer\n")
                f.write("\n".join(mailmap_entries) + "\n")
            print(f"\n.mailmap updated at {mailmap_path}")
            print("Future runs will automatically apply these merges.")
            if config_manager:
                existing_config_entries = config_manager.get("mailmap_entries") or []
                config_manager.set(
                    "mailmap_entries",
                    list(set(existing_config_entries + mailmap_entries))
                )

        return updated_map

    def get_all_authors(self, repo_path: str, config_manager=None) -> Dict[str, str]:
        """
        Returns {canonical_email: display_name} for all contributors.
        Re-uses _parse_log_numstat so we don't iterate commits a second time.
        """
        try:
            mailmap = self._load_mailmap(repo_path, config_manager=config_manager)
            author_data = self._parse_log_numstat(repo_path, mailmap)
            return {email: data["name"] for email, data in author_data.items()}
        except (GitCommandError, ValueError, RuntimeError) as e:
            print(f"  - Warning: Could not read Git authors from '{repo_path}'. Error: {e}")
            return {}
    def get_name_map(self, repo_path: str, config_manager=None) -> Dict[str, str]:
        """
        Returns {canonical_email: display_name} with no diff work.
        Uses git log with format-only (no --numstat), so it's nearly instant.
        Call this instead of get_all_authors() when analyze() has already run.
        """
        mailmap = self._load_mailmap(repo_path, config_manager=config_manager)
        cmd = ["git", "-C", repo_path, "log", "--format=%ae\t%aN"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError:
            raise RuntimeError("git executable not found on PATH")
        author_map: Dict[str, str] = {}
        for line in result.stdout.splitlines():
            parts = line.split("\t", 1)
            if len(parts) == 2:
                email = self._resolve_email(parts[0].strip(), mailmap)
                if email not in author_map:
                    author_map[email] = parts[1].strip()
        return author_map
    
    def analyze(self, repo_path: str) -> Dict[str, ContributionStats]:
        """
        Analyze contributions for all authors.

        The original approach called commit.stats.files (a git subprocess) once
        per commit via GitPython. For a repo with N commits that is N subprocess
        round-trips, typically 30-60s.

        This version issues ONE `git log --numstat` call and stream-parses its
        output. Git internally does the same diff-tree work, but with zero
        per-commit subprocess overhead and no Python object allocation per commit.
        Runtime is dominated by git's own I/O, typically 1-4s for most repos.
        """
        try:
            mailmap = self._load_mailmap(repo_path)
            author_data = self._parse_log_numstat(repo_path, mailmap)
            return {
                email: data["stats"]
                for email, data in author_data.items()
            }
        except (GitCommandError, ValueError, RuntimeError) as e:
            print(f"  - Warning: Could not analyze contributions for '{repo_path}'. Error: {e}")
            return {}

    def calculate_share(self, selected_stats: ContributionStats, total_stats: ContributionStats) -> Dict[str, Any]:
        """
        Given stats for a selected user and the total project, calculates the
        contribution share and returns it as a dictionary.
        """
        total_lines = total_stats.lines_added + total_stats.lines_deleted
        selected_lines = selected_stats.lines_added + selected_stats.lines_deleted
        share = (selected_lines / total_lines * 100) if total_lines > 0 else 0
        return {
            "total_commits": selected_stats.total_commits,
            "lines_added": selected_stats.lines_added,
            "lines_deleted": selected_stats.lines_deleted,
            "contribution_share_percent": round(share, 2),
        }