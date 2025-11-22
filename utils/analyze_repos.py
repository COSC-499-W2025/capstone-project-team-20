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

    """ DELETE BEFORE PR

    As of November 21st, 8am, current output is this, note that author count/status is mangled. 
    Looks like depth --1 is causing this (grabs the latest commit). unfortunate.

    Just forget about this being accurate then, shouldnt need it 

    Last_accessed is not stored by ZIP. Frameworks, skills_used, individual_contributions not yet implemented.

    Storage of variables doesn't work rn because of ProjectAnalyzer, not analyze_repos

    📁 Between-two-worlds
   Authors (1): schutow.kir@yandex.ru
   Status: individual
   Languages: C#, CSS, GLSL, HTML, MATLAB, Objective-C
   Files: 1378
   Size: 132099 KB
   Created: 2025-10-17
   Modified: 2025-11-25




   take a look at categories.yml - file categorizer
    """