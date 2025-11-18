"""
This module clones each repository from repo_dataset.csv onto your machine.

As this will take up storage space on your computer, once you've cloned the repos,
you can run analysis on them, store that analysis locally, and then delete them.
The Project objects associated with the repos will persist.

Workflow:
1. Run 'python3 -m utils.clone_repos.py' to clone repositories into cloned_repos/
2. Run 'python3 -m utils.analyze_cloned_repos' to analyze the repos and store results locally.
3. Run 'python3 -m utils.wipe_repos' to remove the repos from your machine.

Notes: 
- These repos are cloned to the cloned_repos/ directory within our project, where they're organized by repo_label (e.g. mobile_app)
- The repos are shallow clones (--depth 1) only the latest snapshot of each repository is stored, not the full commit history
- cloned_repos/ is ignored by git
"""

import csv
import subprocess
from pathlib import Path
from typing import Tuple, List, Dict


def ensure_gitignore() -> bool:
    """Add cloned_repos/ to .gitignore if not already present."""
    gitignore_path = Path('.gitignore')
    cloned_repos_directory = 'cloned_repos/\n'
    
    if gitignore_path.exists():
        content = gitignore_path.read_text()
        if 'cloned_repos' not in content:
            with open(gitignore_path, 'a') as f:
                f.write(f'\n{cloned_repos_directory}')
            print("Added cloned_repos/ to .gitignore")
        return True
    else:
        print("Error: .gitignore seems to be missing")
        return False


def run_clone_workflow(csv_path: str = 'src/config/repo_dataset.csv', cloned_repos_dir: str = 'cloned_repos') -> None:
    """Clone all repositories from the CSV file."""
    cloned_repos_dir = Path(cloned_repos_dir)
    cloned_repos_dir.mkdir(exist_ok=True)
    
    if not ensure_gitignore():
        return
    
    csv_full_path = Path(csv_path)
    if not csv_full_path.exists():
        print(f"CSV not found: {csv_path}")
        return
    
    with open(csv_full_path) as f:
        repos = list(csv.DictReader(f))
    
    print(f"\n Cloning {len(repos)} repositories...\n")
    
    success_count, skip_count, fail_count = clone_repos(repos, cloned_repos_dir)
    
    print_summary(success_count, skip_count, fail_count)

def clone_repos(repos: List[Dict[str, str]], cloned_repos_dir: Path) -> Tuple[int, int, int]:
    """Clone each repository and return success_count, skipped_count, failed_count"""
    success_count = 0
    skip_count = 0
    fail_count = 0
    for i, row in enumerate(repos, 1):
        repo_name = row['repo_name']
        repo_label = row['repo_label']
        repo_link = row['repo_link']
            
        repo_path = cloned_repos_dir / repo_label / repo_name
            
        if repo_path.exists():
            print(f"[{i}/{len(repos)}] ⏭️  {repo_name} (already exists)")
            skip_count += 1
            continue
        
         # Ensures the parent folder of the current repo_path exists, creates it if not
        repo_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            subprocess.run(
                ['git', 'clone', '--depth', '1', repo_link, str(repo_path)],
                check=True,
                capture_output=True,
                timeout=300,
                text=True
            )
            print(f"[{i}/{len(repos)}] ✅ {repo_name}")
            success_count += 1
                
        except subprocess.TimeoutExpired:
            print(f"[{i}/{len(repos)}] ⏱️  {repo_name} (timeout after 5 minutes)")
            fail_count += 1
                
        except subprocess.CalledProcessError as e:
            print(f"[{i}/{len(repos)}] ❌ {repo_name} (error: {e.stderr.strip()[:60]})")
            fail_count += 1
                
        except Exception as e:
            print(f"[{i}/{len(repos)}] ❌ {repo_name} (error: {str(e)[:60]})")
            fail_count += 1

    return success_count, skip_count, fail_count
    
def print_summary(success_count: int, skip_count: int, fail_count: int) -> None:
    """Print a formatted summary of clone results."""
    print(f"\n{'='*50}")
    print(f"✅ Cloned: {success_count}")
    print(f"⏭️  Skipped: {skip_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"{'='*50}\n")

if __name__ == '__main__':
    run_clone_workflow()
