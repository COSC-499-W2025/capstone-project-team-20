from pathlib import Path
from src.Project import Project
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.ContributionAnalyzer import ContributionAnalyzer
from src.analyzers.language_detector import analyze_language_share, detect_language_per_file
from utils.RepoFinder import RepoFinder
import io, contextlib


class RepoProjectBuilder:
    """
    Replacement for the old GitRepoAnalyzer.
    Scans an extracted directory for Git repositories, maps them to the ZIP's
    internal folder tree, extracts metadata + contributions, then builds
    fully populated Project objects.
    """

    def __init__(self, root_folder):
        """
        root_folder = the ProjectFolder root created by parsing the ZIP.
        This allows us to match repo names to ZIP tree folders.
        """
        self.root_folder = root_folder
        self.repo_finder = RepoFinder()
        self.contribution_analyzer = ContributionAnalyzer()

    def scan(self, extract_dir: Path):
        """
        Main entry point of RepoProjectBuilder.
        Takes an extracted ZIP directory, scans for Git repos, builds Project objects for each repo, returns them as a List.

        Returns:
            List[Project]
        """
        repo_paths = self.repo_finder.find_repos(extract_dir)
        projects = []

        for repo_path in repo_paths:
            proj = self._build_single_project(repo_path)
            if proj:
                projects.append(proj)

        return projects
    
    def suppress_output(self):
        """Silence stdout while running noisy extractors."""
        return contextlib.redirect_stdout(io.StringIO())
    

    # Note: This method is being kept solely for later use. Currently not being used anywhere.
    def _build_full_project(self, repo_path: Path) -> Project:
        """Builds and returns an analyzed Project object."""
        repo_name = repo_path.name

        # 1. Map filesystem repo → ZIP tree folder
        folder = self._find_folder_by_name(self.root_folder, repo_name)
        if not folder:
            print(f"[WARN] Could not map repo folder '{repo_name}' inside ZIP.")
            return None

        # 2. Extract metadata from ZIP tree
        extractor = ProjectMetadataExtractor(folder)
        with self.suppress_output():
            metadata_full = extractor.extract_metadata()
        metadata = metadata_full["project_metadata"]
        category_summary = metadata_full["category_summary"]
        files = extractor.collect_all_files()

        # 3. Contribution stats from actual repo folder
        author_stats = self.contribution_analyzer.analyze(str(repo_path))
        authors = list(author_stats.keys())

        if (len(authors)) <=1:
            if len(folder.subdir) > 1:
                authors = folder.subdir

        # 4. Language share from local repository contents
        language_share = analyze_language_share(str(repo_path))

        # 5. Per-file language detection from ZIP content
        repo_languages = set()
        for f in files:
            lang = detect_language_per_file(Path(f.file_name))
            if lang:
                repo_languages.add(lang)
        repo_languages = sorted(repo_languages)

        # 6. Build Project object
        proj = Project(
            name=repo_name,
            file_path=str(repo_path),
            root_folder=str(folder.name),
            authors=authors,
            author_count=len(authors),
            languages=repo_languages,
            collaboration_status="collaborative" if len(authors)>1 else "individual"
        )

        proj.metadata = metadata
        proj.categories = category_summary
        proj.language_share = language_share

        return proj

    def _build_single_project(self, repo_path: Path) -> Project:
        """Build and return an empty project object, ready for analysis."""
        repo_name = repo_path.name
        folder = self._find_folder_by_name(self.root_folder, repo_name)
        if not folder:
            print(f"[WARN] Could not map repo folder '{repo_name}' inside ZIP.")
            return None

        return Project(
            name=repo_name,
            file_path=str(repo_path),
            root_folder=str(folder.name)
        )


    # Helper to map repo folder to ZIP-tree ProjectFolder
    def _find_folder_by_name(self, folder, target_name):
        """
        Recursively search ZIP tree (ProjectFolder nodes)
        to find a folder whose name matches the repo.
        """
        if folder.name.lower() == target_name.lower():
            return folder

        for sub in folder.subdir:
            found = self._find_folder_by_name(sub, target_name)
            if found:
                return found

        return None
