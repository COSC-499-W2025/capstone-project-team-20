"""
Analyzes all zipped repositories and stores results in the database.

Workflow:
1. Run 'python3 -m utils.clone_repos' to clone repositories
2. Run 'python3 -m utils.zip_repos' to zip them
3. Run 'python3 -m utils.analyze_repos' to analyze  <- THIS SCRIPT
4. Run 'python3 -m utils.wipe_repos' to clean up
"""

from pathlib import Path

from src.analyzers.ProjectAnalyzer import ProjectAnalyzer
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.ZipParser import parse_zip_to_project_folders


def batch_analyze(zipped_repos_dir: str = "zipped_repos") -> None:
    zipped_repos_path = Path(zipped_repos_dir)

    if not zipped_repos_path.exists():
        print(f"Nothing to analyze - {zipped_repos_dir}/ doesn't exist")
        return

    zip_files = list(zipped_repos_path.rglob("*.zip"))
    if not zip_files:
        print(f"No .zip files found in {zipped_repos_dir}/")
        return

    print(f"\nBatch analyzing {len(zip_files)} repositories...\n")

    pa = ProjectAnalyzer()
    analyzed, failed = 0, 0

    for zip_path in zip_files:
        pa._cleanup_temp()
        repo_name = zip_path.stem

        try:
            pa.zip_path = Path(zip_path)
            folders = parse_zip_to_project_folders(str(pa.zip_path))
            pa.root_folder = folders[0]
            pa.metadata_extractor = ProjectMetadataExtractor(pa.root_folder)

            print(f"\n{'=' * 50}")
            print(f"Analyzing: {repo_name}")
            print(f"{'=' * 50}")

            pa.run_all()
            analyzed += 1

        except Exception as e:
            print(f"❌ {repo_name}: {str(e)[:50]}")
            failed += 1

    pa._cleanup_temp()

    print(f"\n{'=' * 40}")
    print(f"Analyzed: {analyzed} | Failed: {failed}")
    print(f"{'=' * 40}\n")


if __name__ == '__main__':
    batch_analyze()