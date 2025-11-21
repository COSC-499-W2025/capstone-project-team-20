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


def run_wipe_workflow(csv_path:str ='src/config/repo_dataset.csv', cloned_repos_dir:str ='cloned_repos') -> None:
    """Delete all cloned repositories."""
    cloned_repos_dir = Path(cloned_repos_dir)
    
    if not cloned_repos_dir.exists():
        print("Nothing to wipe - cloned_repos/ doesn't exist")
        return
    
    csv_full_path = Path(csv_path)
    if not csv_full_path.exists():
        print(f"CSV not found: {csv_path}")
        return
    
    with open(csv_full_path) as f:
        repos = list(csv.DictReader(f))
        
    existing_repos = [
        row for row in repos
        if (cloned_repos_dir / row['repo_label'] / row['repo_name']).exists()
    ]

    if not existing_repos:
        print("No repositories found to delete")
        return

    print(f"\nDeleting {len(existing_repos)} repositories...\n")
    
    deleted_count, failed_count = wipe_repos(existing_repos, cloned_repos_dir)

    clean_up_directories(cloned_repos_dir)
    
    print_summary(deleted_count, failed_count)

def wipe_repos(repos: List[Dict[str,str]], cloned_repos_dir: Path) -> Tuple[int, int]:
    """Deletes repos from your machine, returns deleted_count, failed_count"""
    deleted_count = 0  
    failed_count = 0
    for row in repos:
        repo_name = row['repo_name']
        repo_label = row['repo_label']
        repo_path = cloned_repos_dir / repo_label / repo_name
            
        try:
            shutil.rmtree(repo_path)
            print(f"🗑️  {repo_name}")
            deleted_count += 1
        except Exception as e:
            print(f"❌ Failed to delete {repo_name}: {e}")
            failed_count += 1
    return deleted_count, failed_count

def clean_up_directories(cloned_repos_dir: Path) -> None:
    """Clean up empty label sub-directories and cloned_repos directory"""
    for label_dir in cloned_repos_dir.iterdir():
        if label_dir.is_dir() and not any(label_dir.iterdir()):
            label_dir.rmdir()
            print(f"🗑️  {label_dir.name}/ (empty)")
    
    if not any(cloned_repos_dir.iterdir()):
        cloned_repos_dir.rmdir()
        print(f"🗑️  cloned_repos/ (empty)")
    

def print_summary(deleted_count: int, failed_count:int) -> None:
    """Print a formatted summary of wipe results."""
    print(f"\n{'='*50}")
    print(f"✅ Deleted {deleted_count} repositories")
    if failed_count > 0:
        print(f"❌ Failed: {failed_count}")
    print(f"✨ Disk space reclaimed!")
    print(f"{'='*50}\n")


if __name__ == '__main__':
    run_wipe_workflow()
