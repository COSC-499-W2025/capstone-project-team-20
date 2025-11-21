"""
Zips all cloned repositories for analysis.

Workflow:
1. Run 'python3 -m utils.clone_repos' to clone repositories
2. Run 'python3 -m utils.zip_repos' to zip them  <- THIS SCRIPT
3. Run 'python3 -m utils.analyze_repos' to analyze
4. Run 'python3 -m utils.wipe_repos' to clean up
"""
import shutil
from pathlib import Path
from typing import Tuple


def zip_repos(cloned_dir: str = 'cloned_repos', zipped_dir: str = 'zipped_repos') -> None:
    """Zip all cloned repositories for analysis."""
    cloned_path = Path(cloned_dir)
    zipped_path = Path(zipped_dir)
    
    if not validate_cloned_directory(cloned_path, cloned_dir):
        return
    
    zipped_path.mkdir(exist_ok=True)
    
    repo_paths = find_repos(cloned_path)
    
    if not repo_paths:
        print(f"❌ No repositories found in {cloned_dir}/")
        return
    
    print(f"\n📦 Found {len(repo_paths)} repositories to zip\n")
    
    success_count, fail_count = zip_all_repos(repo_paths, zipped_path)
    
    print_summary(success_count, fail_count, zipped_dir)


def validate_cloned_directory(path: Path, dir_name: str) -> bool:
    """Validate that the cloned_repos directory exists."""
    if not path.exists():
        print(f"❌ Error: {dir_name}/ does not exist")
        print("   Run 'python3 -m utils.clone_repos' first")
        return False
    return True


def find_repos(cloned_path: Path) -> list[Path]:
    """Find all cloned repositories."""
    repo_paths = []
    for label_dir in cloned_path.iterdir():
        if not label_dir.is_dir():
            continue
        for repo_dir in label_dir.iterdir():
            if repo_dir.is_dir() and (repo_dir / '.git').exists():
                repo_paths.append(repo_dir)
    return repo_paths


def zip_all_repos(repo_paths: list[Path], zipped_path: Path) -> Tuple[int, int]:
    """Zip each repository and return success_count, fail_count."""
    success_count = 0
    fail_count = 0
    
    for i, repo_path in enumerate(repo_paths, 1):
        repo_name = repo_path.name
        print(f"[{i}/{len(repo_paths)}] Zipping: {repo_name}")
        
        try:
            zip_name = zipped_path / repo_name
            # CHANGE: Use repo_path.parent as base_dir, and repo_name as root_dir
            # This creates: repo_name.zip -> repo_name/ -> (contents)
            shutil.make_archive(
                str(zip_name), 
                'zip', 
                root_dir=repo_path.parent,  # Start from parent
                base_dir=repo_name           # Include repo folder as root
            )
            success_count += 1
            print(f"  ✅ {repo_name}.zip")
            
        except Exception as e:
            fail_count += 1
            print(f"  ❌ Failed: {e}")
    
    return success_count, fail_count


def print_summary(success_count: int, fail_count: int, zipped_dir: str) -> None:
    """Print a formatted summary of zip results."""
    print(f"\n{'='*50}")
    print(f"✅ Zipped: {success_count}")
    if fail_count > 0:
        print(f"❌ Failed: {fail_count}")
    print(f"📁 Output: {zipped_dir}/")
    print(f"{'='*50}\n")


if __name__ == '__main__':
    zip_repos()