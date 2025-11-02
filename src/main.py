import os
import json
from collections import defaultdict

from src.ConsentManager import ConsentManager
from src.ConfigManager import ConfigManager
from src.ZipParser import parse, extract_zip
from src.analyzers.ProjectMetadataExtractor import ProjectMetadataExtractor
from src.analyzers.GitRepoAnalyzer import GitRepoAnalyzer
from src.analyzers.folder_skill_analyzer import FolderSkillAnalyzer
from src.analyzers.language_detector import analyze_language_share


def _summarize_top_skills(merged, limit=10):
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


def main():
    consent = ConsentManager()

    # (Your testing reset—leave commented in normal runs)
    # ConfigManager().delete("user_consent")

    if not consent.require_consent():
        print("Consent not given. Exiting program.")
        return

    print("Consent confirmed. The application will now proceed.")

    # Get the zip path once
    while True:
        zip_path = input("Please enter the FULL path to the .zip you want to analyze: ").strip()
        if os.path.exists(zip_path) and zip_path.lower().endswith(".zip"):
            break
        print("Invalid path or not a .zip file. Please try again.\n")

    # ---- Extract ZIP to a temp directory for analysis ----
    print("\nExtracting archive...")
    try:
        temp_dir = extract_zip(zip_path)
    except Exception as e:
        print(f"Failed to extract zip: {e}")
        return

    # ---- Analyze Git repos ----
    git_analyzer = GitRepoAnalyzer()
    repo_roots = []
    # Prefer path-based analysis if available; fall back to original .analyze_zip()
    if hasattr(git_analyzer, "_find_and_analyze_repos"):
        try:
            repo_roots = git_analyzer._find_and_analyze_repos(temp_dir)
        except Exception as e:
            print(f"[WARN] Git repo analysis (path-based) failed: {e}")
    else:
        try:
            git_analyzer.analyze_zip(zip_path)
        except Exception as e:
            print(f"[WARN] Git repo analysis (zip-based) failed: {e}")

    # ---- Analyze non-Git folders for skills ----
    folder_analyzer = FolderSkillAnalyzer()
    try:
        repo_roots = set(map(str, repo_roots or []))

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

            # If this folder is inside any repo root, skip (we already analyzed via GitRepoAnalyzer)
            if repo_roots and any(root.startswith(r) for r in repo_roots):
                continue

            # Optionally: only analyze "meaningful" dirs (skip empty and pure metadata dirs)
            if not files:
                continue

            folder_analyzer.analyze_folder(root)

    except Exception as e:
        print(f"[WARN] Folder skill analysis failed: {e}")

    # ---- Display results ----
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
            prof = s.get("proficiency")
            if prof is not None:
                print(f"  • {s['skill']}: presence {s['confidence']*100:.1f}%, proficiency {prof*100:.1f}%")
            else:
                print(f"  • {s['skill']}: presence {s['confidence']*100:.1f}%")


    # ---- Project metadata (your existing flow) ----
    print(f"\nparsing project from: {zip_path}")
    try:
        root_folder = parse(zip_path)
    except Exception as e:
        print(f"Error while parsing: {e}")
        return

    print("\nExtracting project metadata\n")
    try:
        metadata_extractor = ProjectMetadataExtractor(root_folder)
        metadata_extractor.extract_metadata()
    except Exception as e:
        print(f"[WARN] Metadata extraction failed: {e}")

    print("\nextraction is complete!")
    print("\nProgram finished.")



    try:
        root_folder_path = extract_zip(zip_path)
    except Exception as e:
        print(f"Error while extracting: {e}")
        return

    d = analyze_language_share(root_folder_path)
    for language, percentage in d.items():
        print(f"{language}: {percentage}%")

if __name__ == "__main__":
    main()
