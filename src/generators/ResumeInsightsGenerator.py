import random
from datetime import datetime
from typing import Tuple, Dict, Any, List

class ResumeInsightsGenerator:
    """
    Generates resume bullet points and summaries using normalized
    category counts provided by FileCategorizer (VIA ProjectMetadataExtractor)
    """

    def __init__(self, metadata: Dict, categorized_files: Dict, language_share: Dict, project: Any, language_list: List[str]):
        self.metadata = metadata
        self.categorized_files = categorized_files
        self.language_share = language_share
        self.project = project
        self.language_list = language_list
        self.verbs = ["Engineered", "Developed", "Implemented", "Designed", "Built", "Contributed to", "Enhanced"]
        self.impact_phrases = ["improving project clarity", "enhancing maintainability", "supporting long-term scalability"]

    def get_category_counts(self) -> Tuple[int,int,int,int]:
        counts = self.categorized_files or {}
        return counts.get("code", 0), counts.get("docs", 0), counts.get("test", 0) or counts.get("tests", 0), counts.get("config", 0)

    def generate_resume_bullet_points(self) -> list[str]:
        bullets = []
        code_files, doc_files, test_files, config_files = self.get_category_counts()
        team_size = getattr(self.project, "author_count", 1)
        langs_sorted = sorted(self.language_share.items(), key=lambda x: x[1], reverse=True)
        top_langs = ", ".join([lang for lang, pct in langs_sorted[:4]]) if langs_sorted else "multiple languages"

        bullets.append(f"{random.choice(self.verbs)} core features using {top_langs}, contributing to a codebase of {code_files}+ source files.")
        if doc_files > 0 or test_files > 0:
            bullets.append(f"Produced {doc_files}+ documentation files and {test_files} automated tests, {random.choice(self.impact_phrases)}.")

        days = self._compute_days()
        if days > 0:
            bullets.append(f"Iterated on the project across a {self.format_duration(days)} development timeline.")

        if team_size > 1:
            bullets.append(f"Collaborated with a team of {team_size} developers using Git-based workflows.")
        else:
            bullets.append("Independently designed, implemented, and tested all major components.")

        if config_files > 0:
            bullets.append(f"Structured the repository with {config_files} configuration files for optimized clarity.")
        return bullets[:5]

    def generate_project_summary(self) -> str:
        code_files, doc_files, test_files, _ = self.get_category_counts()
        total_files = sum((self.categorized_files or {}).values())
        top_langs = ", ".join(self.language_list[:4]) if self.language_list else "various technologies"
        days = self._compute_days()
        duration_text = f" over {self.format_duration(days)}" if days > 0 else ""
        team_size = getattr(self.project, "author_count", 1)

        summary = (f"A software project built with {top_langs}{duration_text}, containing over {total_files} files, "
                   f"including {code_files} source modules, {test_files} tests, and {doc_files} documentation files. ")
        summary += f"Developed by a team of {team_size}." if team_size > 1 else "Developed independently."
        return summary

    def _compute_days(self) -> int:
        start = self.metadata.get("start_date")
        end = self.metadata.get("end_date")
        if not start or not end: return 0
        if isinstance(start, str): start = datetime.strptime(start, "%Y-%m-%d")
        if isinstance(end, str): end = datetime.strptime(end, "%Y-%m-%d")
        return max((end - start).days, 0)

    def format_duration(self, days: int) -> str:
        if days < 30: return f"{days} days"
        months, rem = divmod(days, 30)
        if rem == 0: return f"{months} month" + ("s" if months > 1 else "")
        return f"{months} month" + ("s" if months > 1 else "") + f" and {rem} days"

    @staticmethod
    def display_insights(bullets: list[str], summary: str) -> None:
        """Called from ProjectAnalyzer, prints resume-specific insights."""
        print("Resume Bullet Points:")
        for b in bullets:
            print(f" • {b}")
        print("\nProject Summary:")
        print(summary)
        print("\n")
