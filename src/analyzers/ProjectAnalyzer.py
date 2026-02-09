import signal, threading
import json, os, sys, re, shutil, contextlib, zipfile
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, Dict, Any

from src.project_timeline import (
    get_projects_with_skills_timeline_from_projects,
    get_skill_timeline_from_projects,
)
from src.analyzers.badge_engine import (
    ProjectAnalyticsSnapshot,
    assign_badges,
    build_fun_facts,
)
from datetime import datetime

from src.ZipParser import parse_zip_to_project_folders, toString, extract_zip
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.FileCategorizer import FileCategorizer
from src.analyzers.language_detector import detect_language_per_file, analyze_language_share
from src.analyzers.ContributionAnalyzer import ContributionAnalyzer, ContributionStats
from utils.RepoFinder import RepoFinder
from src.managers.ProjectManager import ProjectManager
from src.managers.FileHashManager import FileHashManager
from src.models.Project import Project
from src.models.Report import Report
from src.models.ReportProject import ReportProject, PortfolioDetails
from src.ProjectFolder import ProjectFolder
from src.analyzers.SkillAnalyzer import SkillAnalyzer
from src.generators.ResumeInsightsGenerator import ResumeInsightsGenerator
from src.generators.PortfolioGenerator import PortfolioGenerator
from src.managers.ConfigManager import ConfigManager
from src.ProjectRanker import ProjectRanker
from src.analyzers.RepoProjectBuilder import RepoProjectBuilder
from utils.file_hashing import compute_file_hash
from src.exporters.ReportExporter import ReportExporter
from src.managers.ReportManager import ReportManager
from src.services.InsightEditor import InsightEditor


MIN_DISPLAY_CONFIDENCE = 0.5


class ProjectAnalyzer:
    """The main entry point of our program. Caller to all of our dedicated analysis-classes."""

    def __init__(self, config_manager: ConfigManager, root_folders: List[ProjectFolder] = None, zip_path: Path = None):
        self.root_folders: List[ProjectFolder] = root_folders or []
        self.zip_path: Optional[Path] = zip_path
        self._config_manager = config_manager
        self.file_categorizer = FileCategorizer()
        self.repo_finder = RepoFinder()
        self.project_manager = ProjectManager()
        self.file_hash_manager = FileHashManager()
        self.contribution_analyzer = ContributionAnalyzer()
        self.cached_extract_dir: Optional[Path] = None
        self.cached_projects: List[Project] = []
        self.report_manager = ReportManager()
        self.report_exporter = ReportExporter()
        if threading.current_thread() is threading.main_thread():
            signal.signal(signal.SIGINT, self._signal_cleanup)

    @contextlib.contextmanager
    def suppress_output(self):
        with open(os.devnull, "w") as devnull:
            old_stdout, old_stderr, sys.stdout, sys.stderr = sys.stdout, sys.stderr, devnull, devnull
            try:
                yield
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr

    @staticmethod
    def clean_path(raw_input: str) -> Path:
        stripped = raw_input.strip().strip("'").strip('"')
        if os.name == "nt":
            return Path(os.path.expanduser(stripped))
        return Path(os.path.expanduser(re.sub(r'\\(.)', r'\1', stripped)))

    def load_zip(self) -> Tuple[Optional[List[ProjectFolder]], Optional[Path]]:
        try:
            raw_path = input("Please enter the path to the zipped folder: ")
            zip_path = self.clean_path(raw_path)
            while not (os.path.exists(zip_path) and zipfile.is_zipfile(zip_path)):
                raw_path = input("Invalid path or not a zipped file. Please try again: ")
                zip_path = self.clean_path(raw_path)
            print("Parsing ZIP structure...")
            root_folders = parse_zip_to_project_folders(zip_path)
            if not root_folders:
                print("Warning: No projects could be parsed from the zip file.")
            else:
                print(f"Project(s) parsed successfully: {[f.name for f in root_folders]}\n")
            return root_folders, zip_path
        except (KeyboardInterrupt, EOFError):
            return None, None

    def ensure_cached_dir(self) -> Path:
        if self.cached_extract_dir is None and self.zip_path:
            self.cached_extract_dir = Path(extract_zip(str(self.zip_path)))
        return self.cached_extract_dir

    def _get_projects(self) -> List[Project]:
        if not self.cached_projects:
            self.cached_projects = list(self.project_manager.get_all())
        return self.cached_projects

    def _get_zip_project_summary(self, project_name: str) -> Optional[Dict[str, Any]]:
        root_folder = self._find_folder_by_name_recursive(project_name)
        if not root_folder: return None
        extractor = ProjectMetadataExtractor(root_folder)
        return extractor.compute_time_and_size_summary(extractor.collect_all_files())

    def _should_update_project(self, existing: Project, incoming: Project) -> bool:
        if incoming.last_modified and existing.last_modified:
            return incoming.last_modified > existing.last_modified
        return bool(incoming.last_modified and not existing.last_modified)

    def initialize_projects(self) -> List[Project]:
        print("\n--- Initializing Project Records ---")
        if not self.zip_path or not self.root_folders:
            print("No project loaded."); return []
        temp_dir = self.ensure_cached_dir()
        projects_from_builder = RepoProjectBuilder(self.root_folders).scan(temp_dir)
        created_projects: List[Project] = []
        if not projects_from_builder:
            print("No projects found to build."); return []
        print(f"Found {len(projects_from_builder)} project(s). Saving initial records...")
        for proj_new in projects_from_builder:
            if summary := self._get_zip_project_summary(proj_new.name):
                if summary.get("total_files"): proj_new.num_files = int(summary["total_files"])
                if summary.get("total_size_kb"): proj_new.size_kb = int(summary["total_size_kb"])
                if summary.get("start_date"): proj_new.date_created = datetime.strptime(summary["start_date"], "%Y-%m-%d")
                if summary.get("end_date"): proj_new.last_modified = datetime.strptime(summary["end_date"], "%Y-%m-%d")
            proj_existing = self.project_manager.get_by_name(proj_new.name)
            if proj_existing:
                if self._should_update_project(proj_existing, proj_new):
                    proj_existing.file_path, proj_existing.root_folder = proj_new.file_path, proj_new.root_folder
                    proj_existing.last_accessed = datetime.now()
                    self.project_manager.set(proj_existing)
                    print(f"  - Updated existing project: {proj_existing.name}")
                else:
                    print(f"  - Skipped older project version: {proj_existing.name}")
                created_projects.append(proj_existing)
            else:
                proj_new.last_accessed = datetime.now()
                self.project_manager.set(proj_new)
                print(f"  - Created new project record: {proj_new.name} with ID {proj_new.id}")
                created_projects.append(proj_new)
        self.cached_projects = created_projects
        return created_projects

    def _prompt_for_usernames(self, authors: List[str]) -> Optional[List[str]]:
        print("\nPlease select your username(s) from the list of project contributors:")
        if not authors:
            print("No authors found in the commit history."); return None
        for i, author in enumerate(authors):
            print(f"  {i + 1}: {author}")
        print("\nYou can select multiple authors by entering numbers separated by commas (e.g., 1, 3).")
        try:
            choice_str = input("Enter your choice(s) (or 'q' to quit): ").strip()
            if choice_str.lower() == "q": return None
            indices = [int(c.strip()) for c in choice_str.split(",")]
            selected_authors = [authors[i - 1] for i in indices if 0 < i <= len(authors)]
            return sorted(list(set(selected_authors)))
        except (ValueError, IndexError):
            print("Invalid input."); return self._prompt_for_usernames(authors)
        except KeyboardInterrupt:
            print("\nOperation cancelled."); return None

    def _get_or_select_usernames(self, authors: List[str]) -> Optional[List[str]]:
        usernames = self._config_manager.get("usernames")
        if isinstance(usernames, list) and usernames:
            return usernames
        if authors:
            print("\nNo usernames configured. Please select yours from the list of contributors:")
            new_usernames = self._prompt_for_usernames(authors)
            if new_usernames:
                self._config_manager.set("usernames", new_usernames)
                print(f"Usernames '{', '.join(new_usernames)}' have been saved."); return new_usernames
        print("No authors found or selected."); return None

    def analyze_git_and_contributions(self) -> None:
        print("\n--- Git Repository & Contribution Analysis ---")
        projects = list(self.project_manager.get_all())
        if not projects: return

        all_authors = set()
        for project in projects:
            repo_path = Path(project.file_path)
            if (repo_path / ".git").exists():
                all_authors.update(self.contribution_analyzer.get_all_authors(str(repo_path)))

        self._get_or_select_usernames(sorted(list(all_authors)))

        for project in projects:
            repo_path = Path(project.file_path)
            if (repo_path / ".git").exists():
                authors = self.contribution_analyzer.get_all_authors(str(repo_path))
                project.author_count = len(authors)
                project.collaboration_status = "Collaborative" if project.author_count > 1 else "Individual"
                self.project_manager.set(project)
                print(f"\n--- Contributions for: {project.name} ---")
                print(f"  - Total Contributors: {project.author_count}")
                print(f"  - Collaboration Status: {project.collaboration_status}")

    def analyze_metadata(self, projects: Optional[List[Project]] = None) -> None:
        print("\n--- Metadata & File Statistics ---")
        for project in (projects or self._get_projects()):
            print(f"\nAnalyzing metadata for: {project.name}")
            root_folder = self._find_folder_by_name_recursive(project.name)
            if not root_folder:
                print(f"  - Skipping: could not find matching folder."); continue
            with self.suppress_output():
                metadata = (ProjectMetadataExtractor(root_folder).extract_metadata(repo_path=project.file_path) or {}).get("project_metadata", {})
            if "total_files" in metadata: project.num_files = int(metadata["total_files"])
            if "total_size_kb" in metadata: project.size_kb = int(metadata["total_size_kb"])
            if "start_date" in metadata and metadata["start_date"]: project.date_created = datetime.strptime(metadata["start_date"], "%Y-%m-%d")
            if "end_date" in metadata and metadata["end_date"]: project.last_modified = datetime.strptime(metadata["end_date"], "%Y-%m-%d")
            project.last_accessed = datetime.now()
            self.project_manager.set(project)
            print(f"  - Saved metadata for '{project.name}'.")

    def menu_print_metadata_summary(self):
        print("\n===== Project Metadata Summary =====")
        for project in self._get_projects():
            if not project.num_files:
                print(f"\n{project.name}: No metadata analyzed yet."); continue
            summary = { "total_files": project.num_files, "total_size_kb": project.size_kb, "start_date": project.date_created.strftime("%Y-%m-%d") if project.date_created else None, "end_date": project.last_modified.strftime("%Y-%m-%d") if project.last_modified else None, }
            print(f"\n--- {project.name} ---\n{json.dumps(summary, indent=2)}")

    def analyze_categories(self, projects: Optional[List[Project]] = None) -> None:
        print("\n--- File Categories Analysis ---")
        for project in (projects or self._get_projects()):
            print(f"\nAnalyzing categories for: {project.name}")
            root_folder = self._find_folder_by_name_recursive(project.name)
            if not root_folder: continue
            files = ProjectMetadataExtractor(root_folder).collect_all_files()
            file_dicts = [{"path": f.full_path, "language": getattr(f, "language", "Unknown")} for f in files]
            project.categories = self.file_categorizer.compute_metrics(file_dicts).get("counts", {})
            self.project_manager.set(project)
            print(json.dumps(project.categories, indent=2))

    def analyze_languages(self, projects: Optional[List[Project]] = None) -> None:
        print("\n--- Language Detection ---")
        for project in (projects or self._get_projects()):
            print(f"\nProject: {project.name}")
            project_root = Path(project.file_path)
            if not project_root.exists(): continue
            project.language_share = analyze_language_share(project_root)
            project.languages = list(project.language_share.keys())
            self.project_manager.set(project)
            if not project.language_share: print("  - No languages detected."); continue
            for lang, share in project.language_share.items(): print(f"  - {lang}: {share:.1f}%")

    def analyze_skills(self, projects: Optional[List[Project]] = None, silent: bool = False) -> None:
        if not silent: print("\n--- Enriching Projects with Skill Analysis & Scoring ---")
        for project in (projects or list(self.project_manager.get_all())):
            if not silent: print(f"\nAnalyzing skills for: {project.name}...")

            result = SkillAnalyzer(Path(project.file_path)).analyze()
            project.skills_used = sorted([item.skill for item in result['skills'] if item.confidence >= MIN_DISPLAY_CONFIDENCE])

            if dims := result.get('dimensions'):
                if td := dims.get("testing_discipline"): project.testing_discipline_score, project.testing_discipline_level = td.get("score", 0), td.get("level", "")
                if doc := dims.get("documentation_habits"): project.documentation_habits_score, project.documentation_habits_level = doc.get("score", 0), doc.get("level", "")

            if stats := result.get('stats', {}).get("overall"): project.total_loc, project.comment_ratio = stats.get("total_lines_of_code", 0), stats.get("comment_ratio", 0)

            ProjectRanker(project).calculate_resume_score()
            self.project_manager.set(project)
            if not silent: print(f"  - Successfully enriched '{project.name}'. Resume Score: {project.resume_score:.2f}")

    def change_selected_users(self) -> None:
        print("\n--- Change Selected Users ---")
        all_authors = set()
        for project in self._get_projects():
            if (Path(project.file_path) / ".git").exists():
                with self.suppress_output():
                    all_authors.update(self.contribution_analyzer.get_all_authors(str(project.file_path)))
        if not all_authors: print("No Git authors found."); return
        new_usernames = self._prompt_for_usernames(sorted(list(all_authors)))
        if new_usernames:
            self._config_manager.set("usernames", new_usernames)
            print(f"\nSuccessfully updated selected users: {', '.join(new_usernames)}")
        else:
            print("\nNo changes made.")

    def run_all(self) -> None:
        print("\n--- Running All Supported Analyses ---")
        if not list(self.project_manager.get_all()): self.initialize_projects()

        self.analyze_git_and_contributions()
        self.analyze_metadata()
        self.analyze_categories()
        self.analyze_languages()
        self.analyze_skills(silent=True)
        self.display_project_timeline()
        print("\nAll analyses complete.\n")

    def _generate_insights_for_project(self, project: Project):
        if not all([project, project.name, project.file_path, project.categories is not None, project.language_share is not None]):
             print(f"Error: Project '{project.name}' is missing critical data for insight generation.")
             return
        print(f"\n--- Generating Insights for: {project.name} ---")
        root_folder = self._find_folder_by_name_recursive(project.name)
        if not root_folder: print(f"Could not find project '{project.name}'."); return

        with self.suppress_output():
            metadata = (ProjectMetadataExtractor(root_folder).extract_metadata(repo_path=project.file_path) or {}).get("project_metadata", {})
            if (repo_path := Path(project.file_path)) and (repo_path / ".git").exists():
                project.author_count = len(self.contribution_analyzer.get_all_authors(str(repo_path)))
                project.collaboration_status = "Collaborative" if project.author_count > 1 else "Individual"

        resume_gen = ResumeInsightsGenerator(metadata, project.categories, project.language_share, project, project.languages)
        project.bullets = resume_gen.generate_resume_bullet_points()
        project.summary = resume_gen.generate_project_summary()
        portfolio_gen = PortfolioGenerator(metadata, project.categories, project.language_share, project, project.languages)
        project.portfolio_details = portfolio_gen.generate_portfolio_details()
        self.project_manager.set(project)
        print(f"\nGenerated and saved all insights for {project.name}.")
        ResumeInsightsGenerator.display_insights(project.bullets, project.summary)

    def generate_resume_insights(self) -> None:
        self.cached_projects = []
        sorted_projects = self.get_projects_sorted_by_score()
        while True:
            print("\n--- Generate All Project Insights ---")
            print("\nPlease select a project:")
            for i, proj in enumerate(sorted_projects, 1):
                print(f"  {i}: {proj.name} (Score: {proj.resume_score:.2f})")
            print(f"  {len(sorted_projects) + 1}: Generate for ALL scored projects")
            print(f"  {len(sorted_projects) + 2}: Return to Main Menu")
            try:
                choice = int(input("Your choice: ").strip())
                if choice == len(sorted_projects) + 2: return
                selected_projects = sorted_projects if choice == len(sorted_projects) + 1 else [sorted_projects[choice - 1]] if 1 <= choice <= len(sorted_projects) else []
                if not selected_projects: print("Invalid selection."); continue

                for proj_stale in selected_projects:
                    self.run_all()

                    fresh_proj = self.project_manager.get_by_name(proj_stale.name)
                    if not fresh_proj: print(f"Error: Could not reload project {proj_stale.name}."); continue

                    self._generate_insights_for_project(fresh_proj)

                self.cached_projects = []
                return
            except ValueError:
                print("Invalid input.")

    def retrieve_previous_insights(self) -> None:
        print("\n--- Previous Resume Insights ---")
        for project in self._get_projects():
            if project.bullets or project.summary:
                print(f"\n{'='*20}\nInsights for: {project.name}\n{'='*20}")
                ResumeInsightsGenerator.display_insights(project.bullets, project.summary)

    def delete_previous_insights(self) -> None:
        project = self._select_project("Select a project to delete insights from:")
        if not project: return
        project.bullets, project.summary, project.portfolio_details = [], "", PortfolioDetails()
        self.project_manager.set(project)
        print(f"Successfully deleted insights for {project.name}.")

    def _ensure_scores_are_calculated(self) -> List[Project]:
        self.cached_projects = []
        all_projects = list(self.project_manager.get_all())
        projects_needing_score = [p for p in all_projects if p.resume_score == 0]
        if projects_needing_score:
            print("\n  - Calculating resume scores for unscored projects...")
            self.analyze_skills(projects=projects_needing_score, silent=True)
            all_projects = list(self.project_manager.get_all())
            print("  - Score calculation complete.")
        return all_projects

    def get_projects_sorted_by_score(self) -> List[Project]:
        projects = self._ensure_scores_are_calculated()
        return sorted([p for p in projects if p.resume_score > 0], key=lambda p: p.resume_score, reverse=True)

    def display_ranked_projects(self) -> None:
        sorted_projects = self.get_projects_sorted_by_score()
        if not sorted_projects: print("\nNo projects with calculated scores to display."); return
        for project in sorted_projects:
            project.display()

    def display_project_timeline(self) -> None:
        print("\n--- Project & Skill Timeline ---")
        projects = self._get_projects()
        if not projects: return
        rows = get_projects_with_skills_timeline_from_projects(projects)
        print("\n=== Project Timeline (Chronological) ===")
        if not rows: print("No projects with valid dates found.")
        for when, name, skills in rows: print(f"{when.isoformat()} — {name}: {', '.join(skills) if skills else '(no skills)'}")
        events = get_skill_timeline_from_projects(projects)
        if not events: return
        print("\n=== Skill First-Use Timeline ===")
        first_seen = {ev.skill.lower(): ev for ev in reversed(events)}
        for ev in sorted(first_seen.values(), key=lambda e: (e.when, e.skill.lower())): print(f"{ev.when.isoformat()} — {ev.skill} (first seen in {ev.project or 'unknown'})")

    def print_tree(self) -> None:
        print("\n--- Project Folder Structures ---")
        if not self.root_folders: print("No project structure loaded.")
        for root in self.root_folders: print(toString(root))

    def analyze_badges(self) -> None:
        print("\n--- Badge Analysis ---")
        self.cached_projects = []
        project = self._select_project("Select a project to analyze for badges:")
        if not project: return
        self.run_all()
        project = self.project_manager.get_by_name(project.name)

        snapshot = ProjectAnalyticsSnapshot(
            name=project.name, total_files=project.num_files, total_size_kb=project.size_kb, total_size_mb=(project.size_kb / 1024),
            duration_days=(project.last_modified - project.date_created).days if project.last_modified and project.date_created else 0,
            category_summary={"counts": project.categories}, languages=project.language_share, skills=set(project.skills_used),
            author_count=project.author_count, collaboration_status=project.collaboration_status)
        badge_ids, fun_facts = assign_badges(snapshot), build_fun_facts(snapshot, assign_badges(snapshot))
        if badge_ids: print("\nBadges Earned:"); [print(f"  - {b}") for b in badge_ids]
        if fun_facts: print("\nFun Facts:"); [print(f"  • {fact}") for fact in fun_facts]
        print()

    def retrieve_full_portfolio(self) -> None:
        print("\n" + "="*50 + "\n          PROFESSIONAL PORTFOLIO          \n" + "="*50 + "\n")
        portfolio_projects = [p for p in self._get_projects() if p.portfolio_details.project_name]
        if not portfolio_projects: print("No portfolio entries found."); return
        for project in sorted(portfolio_projects, key=lambda x: x.last_modified or datetime.min, reverse=True):
            details = project.portfolio_details
            print(f"### {details.project_name}\n**Role:** {details.role} | **Timeline:** {details.timeline}\n**Technologies:** {details.technologies}\n\n**Project Overview:**\n{details.overview}\n\n**Key Technical Achievements:**\n" + "\n".join(f"* {a}" for a in details.achievements) + "\n" + "-"*50 + "\n")

    def create_report(self) -> Optional[Report]:
        sorted_projects = self.get_projects_sorted_by_score()
        if not sorted_projects:
            print("\nNo scored projects available to create a report.")
            return None

        print("\n--- Create Report ---")
        print("\nSelect one or more projects by entering numbers separated by commas (e.g. 1,3).")
        for i, proj in enumerate(sorted_projects, 1):
            print(f"  {i}: {proj.name} (Score: {proj.resume_score:.2f})")

        choice_str = input("\nYour selection: ").strip().lower()
        if not choice_str:
            print("No projects selected.")
            return None

        try:
            indices = [int(x.strip()) for x in choice_str.split(",")]
            selected_projects_full = [sorted_projects[idx - 1] for idx in indices if 1 <= idx <= len(sorted_projects)]

            if not selected_projects_full:
                print("Invalid project numbers selected.")
                return None

            report_projects = [ReportProject.from_project(p) for p in selected_projects_full]
            title = input("Enter a title for your report (or press Enter for default): ").strip()

            new_report = Report(title=title, projects=report_projects)

            saved_report = self.report_manager.create_report(new_report)

            if saved_report:
                print(f"\nReport created: ID {saved_report.id}, Title: {saved_report.title}")
                return saved_report
            else:
                print("\n❌ Failed to create report.")
                return None

        except ValueError:
            print("Invalid input.")
            return None

    def _get_and_refresh_report(self) -> Optional[Report]:
        print("A PDF is generated from a report. You can create a new report or use an existing one.")
        choice = input("Create (n)ew report or use (e)xisting one? (n/e): ").strip().lower()

        if choice == 'n':
            return self.create_report()

        elif choice == 'e':
            reports = self.report_manager.list_reports()
            if not reports:
                print("\nNo existing reports found.")
                return None
            print("\nAvailable Reports:")
            for r in reports:
                print(f"  ID: {r.id}, Title: {r.title}")
            try:
                report_id = int(input("Enter Report ID: ").strip())
                return self.report_manager.get_report(report_id)
            except (ValueError, TypeError):
                print("Invalid ID.")
                return None
        return None

    def _execute_pdf_generation(self, report, doc_type, generation_func):
        default_filename = f"{report.title.replace(' ', '_').lower()}_{doc_type}.pdf"
        filename = input(f"Output filename (default: '{default_filename}'): ").strip() or default_filename
        if not filename.endswith('.pdf'): filename += '.pdf'

        if input(f"\n✓ Generate {doc_type} as '{filename}'? (y/n): ").strip().lower() != 'y':
            print(f"{doc_type.capitalize()} generation cancelled."); return

        print(f"\n⏳ Generating {doc_type}...")
        try:
            pdf_path = generation_func(report, filename)
            print(f"\n✅ {doc_type.capitalize()} successfully generated! Saved to: {pdf_path}")
        except Exception as e:
            print(f"\n❌ An unexpected error occurred: {e}")

    def trigger_portfolio_generation(self) -> None:
        print("\n--- Generate Portfolio from Report ---")
        report = self._get_and_refresh_report()
        if not report:
            print("Portfolio generation cancelled.")
            return
        if not report.projects:
            print("Error: Report contains no projects. Please create a new report and add projects to it.")
            return

        missing = [p.project_name for p in report.projects if not p.portfolio_details.project_name]
        if missing:
            print(f"\n❌ Cannot generate. Projects missing portfolio details: {', '.join(missing)}")
            print("Please run 'Generate All Project Insights' (Option 10) first."); return
        self._execute_pdf_generation(report, "portfolio", self._generate_portfolio)

    def trigger_resume_generation(self) -> None:
        print("\n--- Generate Resume from Report ---")
        report = self._get_and_refresh_report()
        if not report:
            print("Resume generation cancelled.")
            return
        if not report.projects:
            print("Error: Report contains no projects. Please create a new report and add projects to it.")
            return

        missing = [p.project_name for p in report.projects if not (p.bullets and p.summary)]
        if missing:
            print(f"\n❌ Cannot generate. Projects missing resume insights: {', '.join(missing)}")
            print("Please run 'Generate All Project Insights' (Option 10) first."); return
        self._execute_pdf_generation(report, "resume", self._generate_resume)

    def _generate_portfolio(self, report: Report, output_filename: str) -> Path:
        output_path = Path("portfolios") / output_filename
        self.report_exporter.export_to_pdf(report, self._config_manager, str(output_path), "portfolio")
        return output_path

    def _generate_resume(self, report, output_filename: str) -> Path:
        if not all(self._config_manager.get(f) for f in ["name", "email", "phone"]):
            raise ValueError("Missing personal info. Run 'Configure Personal Info' (18).")
        output_path = Path("resumes") / output_filename
        self.report_exporter.export_to_pdf(report, self._config_manager, str(output_path), "jake")
        return output_path

    def analyze_new_folder(self) -> None:
        self._cleanup_temp()
        root_folders, zip_path = self.load_zip()
        if not zip_path: print("\nNo project loaded."); return
        self.root_folders, self.zip_path = root_folders, zip_path
        self.initialize_projects()

    def configure_personal_info(self) -> None:
        print("\n===== Resume Personal Information =====")
        prompt_value = lambda label, key: self._config_manager.set(key, input(f"{label} [{self._config_manager.get(key, '')}]: ").strip() or self._config_manager.get(key, ''))
        prompt_value("Full name", "name"); prompt_value("Email", "email"); prompt_value("Phone", "phone"); prompt_value("GitHub username", "github"); prompt_value("LinkedIn handle", "linkedin")
        print("Resume personal information saved.\n")

    def _cleanup_temp(self):
        if self.cached_extract_dir: shutil.rmtree(self.cached_extract_dir, ignore_errors=True)

    def _signal_cleanup(self, s, f):
        print("\n[Interrupted] Cleaning up..."); self._cleanup_temp(); sys.exit(0)

    def _find_folder_by_name_recursive(self, target_name: str) -> Optional[ProjectFolder]:
        target_lower = target_name.lower()
        def search(folder: ProjectFolder) -> Optional[ProjectFolder]:
            if folder.name.lower() == target_lower: return folder
            for subfolder in folder.subdir:
                if found := search(subfolder): return found
            return None
        for root in self.root_folders:
            if found := search(root): return found
        return None

    def display_analysis_results(self) -> None:
        print("\n--- Displaying Analysis Results ---")
        self.display_ranked_projects()

    def run(self) -> None:
        if not self.zip_path and (self.root_folders is None or not self.root_folders):
            root_folders, zip_path = self.load_zip()
            if not zip_path:
                print("No project loaded. Exiting.")
                return
            self.root_folders, self.zip_path = root_folders, zip_path

        self.initialize_projects()
        print("\nWelcome to the Project Analyzer.\n")

        while True:
            print("""
                ========================
                Project Analyzer
                ========================
                Choose an option:
                1. Analyze Git Repository & Contributions
                2. Extract Metadata & File Statistics
                3. Categorize Files by Type
                4. Print Project Folder Structure
                5. Analyze Languages Detected
                6. Run All Analyses
                7. Analyze New Folder
                8. Change Selected Users
                9. Analyze Skills (Calculates Resume Score)
                10. Generate All Project Insights
                11. Retrieve Previous Insights
                12. Delete Previous Insights
                13. Display Ranked Projects
                14. Show Project Timeline
                15. Analyze Badges
                16. Retrieve Full Portfolio (CLI View)
                17. Exit
                18. Configure Personal Info
                19. Create Report
                20. Generate Resume from Report
                21. Generate Portfolio from Report
                  """)
            choice = input("Selection: ").strip()
            if not self.zip_path and choice not in ["7", "17"]:
                print("No project loaded. Please analyze a new folder first.")
                continue
            menu = {
                "1": self.analyze_git_and_contributions, "2": self.menu_print_metadata_summary,
                "3": self.analyze_categories, "4": self.print_tree,
                "5": self.analyze_languages, "6": self.run_all,
                "7": self.analyze_new_folder, "8": self.change_selected_users,
                "9": self.analyze_skills, "10": self.generate_resume_insights,
                "11": self.retrieve_previous_insights, "12": self.delete_previous_insights,
                "13": self.display_ranked_projects, "14": self.display_project_timeline,
                "15": self.analyze_badges, "16": self.retrieve_full_portfolio,
                "18": self.configure_personal_info, "19": self.create_report,
                "20": self.trigger_resume_generation,
                "21": self.trigger_portfolio_generation,
            }
            if choice == "17":
                print("Exiting Project Analyzer."); self._cleanup_temp(); return
            if action := menu.get(choice): action()
            else: print("Invalid input. Try again.\n")
