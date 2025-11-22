"""
Zips all cloned repositories for analysis.

Workflow:
1. Run 'python3 -m utils.clone_repos' to clone repositories
2. Run 'python3 -m utils.zip_repos' to zip them  <- THIS SCRIPT
3. Run 'python3 -m utils.analyze_repos' to analyze
4. Run 'python3 -m utils.wipe_repos' to clean up

Notes: 
- These repos are cloned to the zipped_repos/ directory within our project, where they're organized by repo_label (e.g. mobile_app)
- zipped_repos/ is ignored by git
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

    repo_paths = []
    for label_dir in cloned_path.iterdir():
        if not label_dir.is_dir():
            continue
        for repo_dir in label_dir.iterdir():
            if repo_dir.is_dir() and (repo_dir / '.git').exists():
                repo_paths.append((label_dir.name, repo_dir))

    if not repo_paths:
        print(f"❌ No repositories found in {cloned_dir}/")
        return

    print(f"\n📦 Found {len(repo_paths)} repositories to zip\n")

    success_count, skip_count, fail_count = zip_all_repos(repo_paths, zipped_path)
    print_summary(success_count, skip_count, fail_count, zipped_dir)


def validate_cloned_directory(path: Path, dir_name: str) -> bool:
    """Validate that the cloned_repos directory exists."""
    if not path.exists():
        print(f"❌ Error: {dir_name}/ does not exist")
        print("   Run 'python3 -m utils.clone_repos' first")
        return False
    return True


def zip_all_repos(repo_paths: list[tuple[str, Path]], zipped_path: Path) -> Tuple[int, int, int]:
    """Zip each repository and return success_count, skip_count, fail_count."""
    success_count = 0
    skip_count = 0
    fail_count = 0

    for i, (label, repo_dir) in enumerate(repo_paths, 1):
        repo_name = repo_dir.name
        label_zip_dir = zipped_path / label
        zip_file = label_zip_dir / f"{repo_name}.zip"

        if zip_file.exists():
            print(f"[{i}/{len(repo_paths)}] ⏭️  {label}/{repo_name}.zip (already exists)")
            skip_count += 1
            continue

        try:
            label_zip_dir.mkdir(exist_ok=True)
            shutil.make_archive(
                str(label_zip_dir / repo_name),
                'zip',
                root_dir=repo_dir.parent,
                base_dir=repo_name
            )
            print(f"[{i}/{len(repo_paths)}] ✅ {label}/{repo_name}.zip")
            success_count += 1
        except Exception as e:
            print(f"[{i}/{len(repo_paths)}] ❌ Failed {label}/{repo_name}: {e}")
            fail_count += 1

    return success_count, skip_count, fail_count


def print_summary(success_count: int, skip_count: int, fail_count: int, zipped_dir: str) -> None:
    """Print a formatted summary of zip results."""
    print(f"\n{'='*50}")
    print(f"✅ Zipped: {success_count}")
    if skip_count > 0:
        print(f"⏭️  Skipped: {skip_count}")
    if fail_count > 0:
        print(f"❌ Failed: {fail_count}")
    print(f"📁 Output: {zipped_dir}/")
    print(f"{'='*50}\n")


if __name__ == '__main__':
    zip_repos()