# src/analyzers/folder_skill_analyzer.py
"""
folder_skill_analyzer.py

Analyzes a NON-Git folder to infer languages, frameworks, tools, and skills.

Main entry point
- `FolderSkillAnalyzer.analyze_folder(folder_path: str)`:
  - Accepts: absolute or relative directory path.
  - Side effects: appends a result object into `self.analysis_results`.

Result shape (per folder)
{
  "folder_path": "<absolute path>",
  "analysis_data": {
    "skills": [
      {
        "skill": "<name>",               # e.g., "Python", "React", "Docker"
        "confidence": <0..1>,            # presence likelihood
        "proficiency": <0..1>            # heuristic usage depth (see SkillExtractor)
      },
      ...
    ],
    "source": "folder"
  }
}

Workflow overview:
1) Validate the path (must exist & be a directory).
2) Delegate to `SkillExtractor.extract_from_path(Path(folder))` for evidence
   collection from manifests, configs, snippet patterns, and language hints.
3) Convert the resulting `SkillProfileItem`s into a compact payload (top ~12).
4) Store results into `self.analysis_results`.
5) Optional pretty printer: `display_analysis_results()`.

Notes:
- Supported extensions are derived from `LANGUAGE_MAP` in `language_detector`.
- Proficiency is a heuristic. It currently has deeper signals for Python/Docker
  and baseline scoring for common frameworks/tools.
"""

from pathlib import Path
from typing import List, Dict, Any
from .language_detector import LANGUAGE_MAP
from .skill_extractor import SkillExtractor

class FolderSkillAnalyzer:
    """
    Analyzes a folder (not a Git repo) to infer languages, frameworks, and skills.
    """

    def __init__(self):
        self.supported_extensions = set(LANGUAGE_MAP.keys())
        self.skill_extractor = SkillExtractor()
        self.analysis_results: List[Dict[str, Any]] = []

    def analyze_folder(self, folder_path: str) -> None:
        path = Path(folder_path)
        if not path.exists():
            print(f"Path not found: {folder_path}")
            return
        if not path.is_dir():
            print(f"Not a directory: {folder_path}")
            return

        try:
            profile = self.skill_extractor.extract_from_path(path)
            skills_payload = [
                {
                    "skill": s.skill,
                    "confidence": round(s.confidence, 4),
                    "proficiency": round(getattr(s, "proficiency", 0.0), 4),
                }
                for s in profile[:12]
            ]
            self.analysis_results.append({
                "folder_path": str(path),
                "analysis_data": {
                    "skills": skills_payload,
                    "source": "folder"
                },
            })
        except Exception as e:
            print(f"Skill extraction failed for {folder_path}: {e}")

    def display_analysis_results(self) -> None:
        if not self.analysis_results:
            print("No analysis results to display.")
            return

        for result in self.analysis_results:
            path = result["folder_path"]
            skills = result["analysis_data"]["skills"]
            if not skills:
                continue
            print(f"\nFolder: {path}")
            print("-" * (len(path) + 9))
            for s in skills:
                print(
                    f"  • {s['skill']}: "
                    f"presence {s['confidence']*100:.1f}%, "
                    f"proficiency {s['proficiency']*100:.1f}%"
                )

    def get_analysis_results(self) -> List[Dict[str, Any]]:
        return self.analysis_results
