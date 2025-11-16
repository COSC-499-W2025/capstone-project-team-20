import os
import json
import shutil
from collections import defaultdict
from pathlib import Path

from src.ConsentManager import ConsentManager
from src.ConfigManager import ConfigManager  # currently unused, but kept for future toggles
from src.ZipParser import parse, extract_zip
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.analyzers.folder_skill_analyzer import FolderSkillAnalyzer
from src.analyzers.language_detector import analyze_language_share  # optional, not used yet
from src.DocumentScraper import process_directory


def _summarize_top_skills(merged, limit: int = 10):
    """
    Build a simple 'top skills' summary across git + folders,
    taking the max confidence seen for each skill.
    """
    acc = defaultdict(float)
    for group in ("git", "folders"):
        for item in merged.get(group, []):
            skills = (item.get("analysis_data") or {}).get("skills") or []
            for s in skills:
                # keep the highest confidence observed
                acc[s["skill"]] = max(acc[s["skill"]], float(s["confidence"]))
    top = sorted(acc.items(), key=lambda x: -x[1])[:limit]
    return [{"skill": k, "confidence": round(v, 4)} for k, v in top]


def _prompt_for_zip_path() -> str:
    """
    Prompt user until a valid .zip path is provided.
    Normalizes quotes and ~.
    """
    while True:
        zip_path = input("Please enter the path to the zip file you want to analyze: ").strip()
        zip_path = zip_path.strip("'\"")
        path_obj = Path(zip_path).expanduser()
        if path_obj.exists() and path_obj.suffix.lower() == ".zip":
            return str(path_obj)
        print("Invalid path or not a .zip file. Please try again.\n")


def main():
    """
    Main application entry point. Manages user consent, input, and orchestrates
    the analysis and document scraping of a provided zip archive.
    """
    consent = ConsentManager()

    # Optional manual reset hook (leave commented in normal runs)
    # ConfigManager().delete("user_consent")

    if not consent.require_consent():
        print("Consent not given. Exiting program.")
        return

    print("Consent confirmed. The application will now proceed.")

    # --- Get the zip path once, robustly ---
    zip_path = _prompt_for_zip_path()

    temp_dir = None
    try:
        # ---- Extract ZIP to a temp directory for analysis ----
        print("\nExtracting archive...")
        temp_dir = extract_zip(zip_path)

        # ---- Analyze Git repos (path-based, single extraction) ----
        print("\nRunning Git repository analysis...")
        git_analyzer = GitRepoAnalyzer()
        repo_roots = []
        try:
            if hasattr(git_analyzer, "_find_and_analyze_repos"):
                # May or may not return repo roots depending on version; both are acceptable.
                result = git_analyzer._find_and_analyze_repos(temp_dir)
                repo_roots = result or []
            else:
                # Fallback: zip-based API (uses its own temp dir internally)
                git_analyzer.analyze_zip(zip_path)
                repo_roots = []
        except Exception as e:
            print(f"[WARN] Git repo analysis failed: {e}")
            repo_roots = []

        print("\nGit analysis complete.")

        # ---- Analyze non-Git folders for skills ----
        folder_analyzer = FolderSkillAnalyzer()
        try:
            repo_root_strs = {str(r) for r in repo_roots} if repo_roots else set()

            SKIP_DIRS = {
                ".git",
                "__pycache__",
                ".pytest_cache",
                ".mypy_cache",
                ".venv",
                "venv",
                "node_modules",
                ".idea",
                ".vscode",
                "__MACOSX",
            }

            for root, dirs, files in os.walk(temp_dir):
                # mutate dirs in-place so os.walk doesn't descend into them
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

                # If this folder is inside any repo root, skip (already covered by GitRepoAnalyzer)
                if repo_root_strs and any(root.startswith(r) for r in repo_root_strs):
                    continue

                if not files:
                    continue

                folder_analyzer.analyze_folder(root)

        except Exception as e:
            print(f"[WARN] Folder skill analysis failed: {e}")

        # ---- Display results from both analyzers ----
        print("\n=== GIT REPOSITORIES ===")
        if hasattr(git_analyzer, "display_analysis_results"):
            git_analyzer.display_analysis_results()
        else:
            print("(No printer for Git analyzer; implement display_analysis_results())")

        print("\n=== NON-GIT FOLDERS ===")
        folder_analyzer.display_analysis_results()

        # ---- Build merged structure and print a Top Skills summary ----
        merged = {
            "git": getattr(git_analyzer, "analysis_results", []),
            "folders": folder_analyzer.get_analysis_results(),
        }

        top_skills = _summarize_top_skills(merged, limit=12)
        if top_skills:
            print("\n=== INFERRED TOP SKILLS ===")
            for s in top_skills:
                # top summary only tracks presence; proficiency remains per-folder detail
                print(f"  • {s['skill']}: presence {s['confidence']*100:.1f}%")

        # ---- Project metadata (ZipParser -> ProjectMetadataExtractor) ----
        print(f"\nParsing project structure from: {zip_path}")
        try:
            root_folder = parse(zip_path)
            metadata_extractor = ProjectMetadataExtractor(root_folder)
            print("\nExtracting project metadata\n")
            metadata_extractor.extract_metadata()
        except Exception as e:
            print(f"[WARN] Metadata extraction failed: {e}")

        # ---- Document scraping on extracted filesystem tree ----
        try:
            scraped_data = process_directory(temp_dir)
            if not scraped_data:
                print("\nNo supported documents (.txt, .pdf, .docx) were found for scraping.")
            else:
                print(f"\nSummary: Aggregated text from {len(scraped_data)} document(s).")
                # scraped_data remains available here for downstream consumers if needed
        except Exception as e:
            print(f"[WARN] Document scraping failed: {e}")

    except Exception as e:
        print(f"\nAn unexpected error occurred during the process: {e}")
    finally:
        # Ensure the temporary directory is always removed, even if errors occur.
        if temp_dir and os.path.exists(temp_dir):
            print(f"\nCleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir)

        print("\nProgram finished.")


if __name__ == "__main__":
    main()
