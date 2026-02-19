from datetime import datetime
from typing import Dict, Any, List
from src.models.ReportProject import PortfolioDetails


class PortfolioGenerator:
    """
    Generates structured portfolio entries for projects.
    This class is responsible for creating a detailed, structured
    PortfolioDetails object for a single project.
    """

    def __init__(
        self,
        metadata: Dict,
        categorized_files: Dict,
        language_share: Dict,
        project: Any,
        language_list: List[str],
    ):
        self.metadata = metadata
        self.categorized_files = categorized_files
        self.language_share = language_share
        self.project = project
        self.language_list = language_list

    def generate_portfolio_details(self) -> PortfolioDetails:
        """
        Generates a structured PortfolioDetails object with no Markdown.
        """
        code_files, _, _, _ = self._get_category_counts()
        total_files = sum((self.categorized_files or {}).values())

        days = self._compute_days()
        duration_str = self._format_duration(days)

        langs = ", ".join(self.language_list[:4]) if self.language_list else "various technologies"

        team_count = getattr(self.project, "author_count", 0)
        if team_count > 1:
            role = f"Team Contributor (Team of {team_count})"
            collaboration_text = f"collaborated with {team_count-1} other developers to build"
        else:
            role = "Solo Developer"
            collaboration_text = "independently designed and implemented"

        project_name = getattr(self.project, "name", "Project")

        overview = (
            f"A software solution {collaboration_text} over a {duration_str} period. "
            f"The codebase consists of {total_files} files, including {code_files} source modules, "
            f"structured for maintainability and scalability."
        )

        achievements = []
        test_ratio = getattr(self.project, "test_file_ratio", 0)
        if test_ratio > 0.15:
            achievements.append("Implemented a robust automated testing suite ensuring high code reliability.")
        elif test_ratio > 0:
            achievements.append("Integrated automated tests to support continuous integration.")
        doc_score = getattr(self.project, "documentation_habits_score", 0)
        if doc_score > 75:
            achievements.append("Maintained comprehensive documentation to facilitate developer onboarding and maintenance.")
        loc = getattr(self.project, "total_loc", 0)
        if loc > 5000:
            achievements.append(f"Architected a substantial codebase of over {loc:,} lines of code.")
        if not achievements:
            achievements.append("Delivered a functional codebase using modern development practices.")

        return PortfolioDetails(
            project_name=project_name,
            role=role,
            timeline=duration_str,
            technologies=langs,
            overview=overview,
            achievements=achievements
        )

    def _get_category_counts(self) -> tuple[int, int, int, int]:
        counts = self.categorized_files or {}
        code_files = counts.get("code", 0)
        doc_files = counts.get("docs", 0)
        test_files = counts.get("test", 0) or counts.get("tests", 0)
        config_files = counts.get("config", 0)
        return code_files, doc_files, test_files, config_files

    def _compute_days(self) -> int:
        start = self.metadata.get("start_date")
        end = self.metadata.get("end_date")
        if not start or not end:
            return 0
        if isinstance(start, str):
            start = datetime.strptime(start, "%Y-%m-%d")
        if isinstance(end, str):
            end = datetime.strptime(end, "%Y-%m-%d")
        return max((end - start).days, 0)

    def _format_duration(self, days: int) -> str:
        if days < 30:
            return f"{days} days"
        months, rem = divmod(days, 30)
        if rem == 0:
            return f"{months} month" + ("s" if months > 1 else "")
        return f"{months} month" + ("s" if months > 1 else "") + f" and {rem} days"
