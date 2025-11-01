# src/analyzers/folder_skill_analyzer.py

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
                {"skill": s.skill, "confidence": round(s.confidence, 4)}
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
            print(f"\nFolder: {result['folder_path']}")
            print("-" * (len(result['folder_path']) + 9))
            for s in result["analysis_data"]["skills"]:
                print(f"  • {s['skill']}: {s['confidence']*100:.1f}%")
        print()

    def get_analysis_results(self) -> List[Dict[str, Any]]:
        return self.analysis_results
