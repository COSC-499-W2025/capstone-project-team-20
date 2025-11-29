"""
This module wipes each repository from repo_dataset.csv from your machine.
For use after cloning and analyzing the repos to reclaim disk space.

Workflow:
1. python3 -m utils.clone_repos
2. python3 -m utils.zip_repos
3. python3 -m utils.analyze_repos
4. python3 -m utils.wipe_repos <- THIS SCRIPT
"""

import csv
import shutil
from pathlib import Path
from typing import Dict, List, Tuple


def run_wipe_workflow(csv_path: str, repos_dir: str) -> None:
    """Delete all cloned repositories."""
    repos_dir = Path(repos_dir)
    
    if not repos_dir.exists():
        print(f"Nothing to wipe - {repos_dir}/ doesn't exist")
        return

    csv_full_path = Path(csv_path)
    if not csv_full_path.exists():
        print(f"CSV not found: {csv_path}")
        return

    with open(csv_full_path) as f:
        repos = list(csv.DictReader(f))

    existing_repos = []
    for row in repos:
        repo_name = row['repo_name']
        repo_label = row['repo_label']
        repo_dir = repos_dir / repo_label / repo_name
        repo_zip = repos_dir / repo_label / f"{repo_name}.zip"

        if repo_dir.exists() or repo_zip.exists():
            existing_repos.append(row)

    if not existing_repos:
        print("No repositories found to delete")
        return

    print(f"\nDeleting {len(existing_repos)} repositories...\n")

    deleted_count, failed_count = wipe_repos(existing_repos, repos_dir)
    clean_up_directories(repos_dir)
    print_summary(deleted_count, failed_count)


def wipe_repos(repos: List[Dict[str, str]], repos_dir: Path) -> Tuple[int, int]:
    """Deletes repos (directories and zips) from your machine, returns deleted_count, failed_count."""
    deleted_count = 0
    failed_count = 0

    for row in repos:
        repo_name = row['repo_name']
        repo_label = row['repo_label']
        repo_path = repos_dir / repo_label / repo_name
        repo_zip = repos_dir / repo_label / f"{repo_name}.zip"

        try:
            if repo_path.is_dir():
                shutil.rmtree(repo_path)
                print(f"🗑️  {repo_name}/")
            if repo_zip.exists():
                repo_zip.unlink()
                print(f"🗑️  {repo_name}.zip")
            deleted_count += 1
        except Exception as e:
            print(f"❌ Failed to delete {repo_name}: {e}")
            failed_count += 1

    return deleted_count, failed_count


def clean_up_directories(repos_dir: Path) -> None:
    """Clean up empty label sub-directories and repo directory."""
    for label_dir in repos_dir.iterdir():
        if label_dir.is_dir() and not any(label_dir.iterdir()):
            label_dir.rmdir()
            print(f"🗑️  {label_dir.name}/ (empty)")

    if not any(repos_dir.iterdir()):
        repos_dir.rmdir()
        print(f"🗑️  {repos_dir}/ (empty)")


def print_summary(deleted_count: int, failed_count: int) -> None:
    """Print a formatted summary of wipe results."""
    print(f"\n{'='*50}")
    print(f"✅ Deleted {deleted_count} repositories")
    if failed_count > 0:
        print(f"❌ Failed: {failed_count}")
    print(f"✨ Disk space reclaimed!")
    print(f"{'='*50}\n")


if __name__ == '__main__':
    run_wipe_workflow('src/config/repo_dataset.csv', 'cloned_repos')
    run_wipe_workflow('src/config/repo_dataset.csv', 'zipped_repos')