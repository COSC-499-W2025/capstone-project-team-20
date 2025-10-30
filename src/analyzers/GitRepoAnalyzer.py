import os
import shutil
from pathlib import Path
from typing import Set, List, Dict, Any

from git import Repo, GitCommandError

from .language_detector import LANGUAGE_MAP
from src.ZipParser import extract_zip

from .skill_extractor import SkillExtractor


class GitRepoAnalyzer:
    """
    Analyzes projects within a zip archive to determine file authorship.

    This class orchestrates the analysis of projects extracted from a
    zip archive. The results are stored in memory and can be displayed
    in a readable format.
    """

    def __init__(self) -> None:
        """
        Initializes the Repository Analyzer.
        """
        self.analysis_results: List[Dict[str, Any]] = []
        # LANGUAGE_MAP keys are extensions *without* the dot
        self.supported_extensions = set(LANGUAGE_MAP.keys())
        # Skill extractor (repo/folder mode)
        self.skill_extractor = SkillExtractor()

    def analyze_zip(self, zip_path: str) -> None:
        """
        Analyzes the contents of a zip archive.

        Args:
            zip_path: The path to the .zip file to be analyzed.
        """
        temp_dir = None
        try:
            temp_dir = extract_zip(zip_path)
            print("Starting analysis...")
            self._find_and_analyze_repos(temp_dir)
            print("Analysis complete.")
            self.display_analysis_results()
        except ValueError as e:
            print(e)
        finally:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temporary directory: {temp_dir}")

    def _find_and_analyze_repos(self, base_dir: str) -> None:
        """
        Recursively finds and analyzes all Git repositories in a directory.
        """
        for root, dirs, _ in os.walk(base_dir):
            if "__MACOSX" in root:
                continue
            if ".git" in dirs:
                repo_path = Path(root)
                project_name = repo_path.name
                print(f"Found Git repository for project: {project_name}")
                self._analyze_repository(repo_path, project_name)
                # Stop searching deeper in this directory to avoid analyzing submodules as separate projects
                dirs.clear()

    def _analyze_repository(self, repo_path: Path, project_name: str) -> None:
        """
        Analyzes a single Git repository to determine file authorship
        and infers project skills (once per repo).
        """
        try:
            repo = Repo(repo_path)
        except GitCommandError as e:
            print(f"Error opening repository at {repo_path}: {e}")
            return

        # Using traverse() to iterate through all files in the commit
        for item in repo.head.commit.tree.traverse():
            """
            In Git's object model, files are represented as "blobs".
            This check ensures we are only processing files, not directories or other object types.
            """
            if item.type == 'blob':
                file_path = item.path
                # Skip files with unsupported extensions
                ext = Path(file_path).suffix.lstrip(".").lower()
                if ext not in self.supported_extensions:
                    continue

                authors: Set[str] = set()
                try:
                    # Retrieve all commits that modified this file path
                    commits = list(repo.iter_commits(paths=file_path))
                    if not commits:
                        # Skip files that have no commit history (e.g., added but not committed)
                        continue
                    for commit in commits:
                        authors.add(commit.author.email)
                except Exception as e:
                    # This can happen for various reasons, e.g., issues with file paths or commit data
                    print(f"Could not process file {file_path} in {project_name}: {e}")
                    continue

                author_count = len(authors)
                analysis_data = {
                    "author_count": author_count,
                    "collaboration_status": "collaborative" if author_count > 1 else "individual"
                }

                # Store per-file authorship result in memory
                self.analysis_results.append({
                    "file_path": file_path,
                    "project_name": project_name,
                    "analysis_data": analysis_data,
                })

        # --- Repo-level skill inference (run once per repo) ---
        try:
            profile = self.skill_extractor.extract_from_path(repo_path)
            skills_payload = [
                {"skill": s.skill, "confidence": round(s.confidence, 4)}
                for s in profile[:12]
            ]
            self.analysis_results.append({
                "file_path": "<repo>",
                "project_name": project_name,
                "analysis_data": {
                    "skills": skills_payload
                },
            })
        except Exception as e:
            print(f"Skill extraction failed for {project_name}: {e}")

    def display_analysis_results(self) -> None:
        """
        Groups results by project and prints them in a readable format.
        """
        if not self.analysis_results:
            print("No analysis results to display.")
            return

        # Group results by project name for structured output
        results_by_project: Dict[str, List[Dict[str, Any]]] = {}
        for result in self.analysis_results:
            project_name = result["project_name"]
            if project_name not in results_by_project:
                results_by_project[project_name] = []
            results_by_project[project_name].append(result)

        print("\n" + "="*30)
        print("      Analysis Results")
        print("="*30 + "\n")

        for project_name, results in results_by_project.items():
            print(f"Project: {project_name}")
            print("-" * (len(project_name) + 9))

            # Show repo-level skills first (if present)
            repo_cards = [r for r in results if r["file_path"] == "<repo>" and "skills" in r["analysis_data"]]
            if repo_cards:
                skills = repo_cards[0]["analysis_data"]["skills"]
                if skills:
                    print("  Inferred skills:")
                    for s in skills:
                        # confidence already 0..1, present as %
                        print(f"    • {s['skill']}: {s['confidence']*100:.1f}%")
                    print()

            # Then list per-file authorship
            file_cards = [r for r in results if r["file_path"] != "<repo>"]
            for result in sorted(file_cards, key=lambda x: x['file_path']):
                analysis = result['analysis_data']
                print(f"  - File: {result['file_path']}")
                print(f"    Authors: {analysis['author_count']}")
                print(f"    Status: {analysis['collaboration_status']}\n")
            print("\n")

    def get_analysis_results(self) -> List[Dict[str, Any]]:
        """
        Retrieves all analysis results.

        Returns:
            A list of dictionaries containing the analysis data for each file.
        """
        return self.analysis_results
