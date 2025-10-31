"""
Coordinator for running both GitRepoAnalyzer and FolderSkillAnalyzer
on any zip archive (mixed projects: git repos + plain folders).
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
