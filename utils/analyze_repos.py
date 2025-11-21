"""
Analyzes all zipped repositories and stores results in the database.

Workflow:
1. Run 'python3 -m utils.clone_repos' to clone repositories
2. Run 'python3 -m utils.zip_repos' to zip them
3. Run 'python3 -m utils.analyze_repos' to analyze  <- THIS SCRIPT
4. Run 'python3 -m utils.wipe_repos' to clean up

This script:
- Reads each .zip file from zipped_repos/
- Runs GitRepoAnalyzer to extract author/collaboration data
- Parses zip structure and extracts metadata (files, size, dates)
- Detects languages used in the project
- Persists Project objects to the database via ProjectManager
- Cleans up temporary files
"""

import shutil
from pathlib import Path
from typing import List, Optional, Set, Tuple

from src.ZipParser import parse, extract_zip
from src.ProjectManager import ProjectManager
from src.Project import Project
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.language_detector import detect_language_per_file
from utils.RepoFinder import RepoFinder


def run_analysis_workflow(zipped_dir: str = 'zipped_repos') -> None:
    """Analyze all zipped repositories and persist results."""
    zipped_path = Path(zipped_dir)
    
    if not validate_zipped_directory(zipped_path):
        return
    
    zip_files = list(zipped_path.glob('*.zip'))
    
    if not zip_files:
        print(f"❌ No .zip files found in {zipped_dir}/")
        return
    
    print(f"\n🔍 Found {len(zip_files)} repositories to analyze\n")
    
    repo_finder = RepoFinder()
    project_manager = ProjectManager()
    git_analyzer = GitRepoAnalyzer(repo_finder, project_manager)
    
    success_count, fail_count, projects = analyze_all_zips(
        zip_files, git_analyzer, project_manager
    )
    
    print_summary(success_count, fail_count)
    display_results(projects)


def validate_zipped_directory(path: Path) -> bool:
    """Validate that the zipped_repos directory exists."""
    if not path.exists():
        print(f"❌ Error: {path}/ does not exist")
        print("   Run 'python3 -m utils.zip_repos' first")
        return False
    return True


def analyze_all_zips(
    zip_files: List[Path], 
    git_analyzer: GitRepoAnalyzer,
    project_manager: ProjectManager
) -> Tuple[int, int, List[Project]]:
    """
    Analyze each zip file and return success_count, fail_count, and projects.
    """
    success_count = 0
    fail_count = 0
    all_projects: List[Project] = []
    
    for i, zip_path in enumerate(zip_files, 1):
        repo_name = zip_path.stem
        print(f"[{i}/{len(zip_files)}] Analyzing: {repo_name}")
        
        temp_dir = None
        try:
            # Run git analysis (extracts to temp dir internally)
            temp_dir = extract_zip(str(zip_path))
            temp_path = Path(temp_dir)
            
            git_projects = git_analyzer.run_analysis_from_path(temp_path)
            
            if git_projects:
                project = git_projects[0]
            else:
                # No git repo found, create a basic project
                project = Project(name=repo_name)
            
            # Parse zip structure for metadata/language analysis
            root_folder = parse(str(zip_path))
            
            # Run metadata extraction
            enrich_with_metadata(project, root_folder)
            
            # Run language detection
            enrich_with_languages(project, root_folder)
            
            # Store file path
            project.file_path = str(zip_path)
            project.root_folder = root_folder.name if root_folder else ""
            
            # Persist to database
            project_manager.set(project)
            all_projects.append(project)
            success_count += 1
            print(f"  ✅ {repo_name}")
                
        except Exception as e:
            fail_count += 1
            print(f"  ❌ {repo_name} (error: {str(e)[:60]})")
            
        finally:
            if temp_dir and Path(temp_dir).exists():
                shutil.rmtree(temp_dir)
    
    return success_count, fail_count, all_projects


def enrich_with_metadata(project: Project, root_folder) -> None:
    """Extract metadata from parsed folder tree and populate Project fields."""
    if not root_folder:
        return
    
    extractor = ProjectMetadataExtractor(root_folder)
    files = extractor.collect_all_files()
    
    if not files:
        return
    
    summary = extractor.compute_time_and_size_summary(files)
    
    if summary:
        # Note: keys in summary have trailing colons (e.g., "total_files:")
        project.num_files = summary.get("total_files:", 0)
        project.size_kb = int(summary.get("total_size_kb:", 0))
        
        start_date = summary.get("start_date:")
        end_date = summary.get("end_date:")
        
        if start_date:
            try:
                from datetime import datetime
                project.date_created = datetime.strptime(start_date, "%Y-%m-%d")
            except ValueError:
                pass
        
        if end_date:
            try:
                from datetime import datetime
                project.last_modified = datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                pass


def enrich_with_languages(project: Project, root_folder) -> None:
    """Detect languages from parsed folder tree and populate Project fields."""
    if not root_folder:
        return
    
    extractor = ProjectMetadataExtractor(root_folder)
    files = extractor.collect_all_files()
    
    if not files:
        return
    
    languages: Set[str] = set()
    
    for f in files:
        lang = detect_language_per_file(Path(f.file_name))
        if lang:
            languages.add(lang)
    
    project.languages = sorted(list(languages))


def print_summary(success_count: int, fail_count: int) -> None:
    """Print a formatted summary of analysis results."""
    print(f"\n{'='*50}")
    print(f"✅ Analyzed: {success_count}")
    if fail_count > 0:
        print(f"❌ Failed: {fail_count}")
    print(f"💾 Results saved to projects.db")
    print(f"{'='*50}")


def display_results(projects: List[Project]) -> None:
    """Display a summary of analyzed projects."""
    if not projects:
        print("\nNo projects to display.")
        return
    
    print(f"\n{'='*50}")
    print("      Analyzed Projects")
    print(f"{'='*50}\n")
    
    for project in projects:
        print(f"📁 {project.name}")
        if project.authors:
            print(f"   Authors ({project.author_count}): {', '.join(project.authors)}")
        print(f"   Status: {project.collaboration_status}")
        if project.languages:
            print(f"   Languages: {', '.join(project.languages)}")
        if project.num_files:
            print(f"   Files: {project.num_files}")
        if project.size_kb:
            print(f"   Size: {project.size_kb} KB")
        print()


if __name__ == '__main__':
    run_analysis_workflow()