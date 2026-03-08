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
from src.managers.ConfigManager import ConfigManager
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

    analyzed, failed = 0, 0

    for zip_path in zip_files:
        repo_name = zip_path.stem

        try:
            folders = parse_zip_to_project_folders(str(zip_path))
            if not folders:
                raise ValueError("No project folders found in zip")

            cm = ConfigManager()
            pa = ProjectAnalyzer(cm, folders, zip_path)

            print(f"\n{'=' * 50}")
            print(f"Analyzing: {repo_name}")
            print(f"{'=' * 50}")

            # Initialize only this repo's project(s), scoped to current zip
            projects = pa.initialize_projects()
            if not projects:
                raise ValueError("Initialization produced no projects")

            # Run each analysis step scoped to only this batch
            pa.analyze_git_and_contributions(projects=projects, interactive=False)
            pa.analyze_metadata(projects=projects)
            pa.analyze_categories(projects=projects)
            pa.analyze_languages(projects=projects)
            pa.analyze_skills(projects=projects)
            analyzed += 1

        except Exception as e:
            print(f"❌ {repo_name}: {str(e)[:80]}")
            failed += 1

    print(f"\n{'=' * 40}")
    print(f"Analyzed: {analyzed} | Failed: {failed}")
    print(f"{'=' * 40}\n")


if __name__ == '__main__':
    batch_analyze()