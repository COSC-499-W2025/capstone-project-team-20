"""
analyze_any.py

Coordinator for running both GitRepoAnalyzer and FolderSkillAnalyzer
on any zip archive (mixed projects: git repos + plain folders).

Main entry point
- `analyze_zip_any(zip_path: str)`:
  - Accepts: path to a .zip file containing one or more projects.
  - Side effects: extracts the zip to a temp dir, analyzes both Git repos and
    regular folders, and prints summarized results to stdout.

Returns
- This module prints results; it does not return them. (Keep using
  the analyzers' `get_analysis_results()` if you need programmatic access.)

Workflow overview:
1) `extract_zip`: unzip archive into a temporary directory.
2) Git scan:
   - `GitRepoAnalyzer._find_and_analyze_repos(temp_dir)` discovers any nested
     repos and runs its internal analysis over each.
3) Folder scan (non-Git):
   - Walk the extracted tree; for any folder that is NOT within a detected repo
     and not a metadata folder (e.g., `__MACOSX`), call
     `FolderSkillAnalyzer.analyze_folder(root)`.
4) Print:
   - Print a "GIT REPOSITORIES" section using the git analyzer's display method.
   - Print a "NON-GIT FOLDERS" section using the folder analyzer's display method.

Notes:
- `GitRepoAnalyzer` may require `gitpython` in the runtime environment.
- The folder analyzer infers skills from file patterns and manifests; it does
  not execute code.
"""

import os
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.analyzers.folder_skill_analyzer import FolderSkillAnalyzer
from src.ZipParser import extract_zip


def analyze_zip_any(zip_path: str):
    """
    Extracts the zip, analyzes both Git repos and regular folders for skills,
    and prints summarized results.
    """
    temp_dir = extract_zip(zip_path)
    git_analyzer = GitRepoAnalyzer()
    folder_analyzer = FolderSkillAnalyzer()

    # Analyze Git repos
    repo_roots = git_analyzer._find_and_analyze_repos(temp_dir)

    # Analyze remaining folders (non-Git)
    for root, dirs, files in os.walk(temp_dir):
        if ".git" in dirs or "__MACOSX" in root:
            continue
        if not any(str(root).startswith(str(r)) for r in repo_roots):
            folder_analyzer.analyze_folder(root)

    print("\n=== GIT REPOSITORIES ===")
    git_analyzer.display_analysis_results()

    print("\n=== NON-GIT FOLDERS ===")
    folder_analyzer.display_analysis_results()
