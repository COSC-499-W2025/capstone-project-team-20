"""
Analyzes all zipped repositories and stores results in the database.

Workflow:
1. Run 'python3 -m utils.clone_repos' to clone repositories
2. Run 'python3 -m utils.zip_repos' to zip them
3. Run 'python3 -m utils.analyze_repos' to analyze  <- THIS SCRIPT
4. Run 'python3 -m utils.wipe_repos' to clean up
"""
from src.analyzers.ProjectAnalyzer import ProjectAnalyzer

if __name__ == '__main__':
    ProjectAnalyzer().batch_analyze()
