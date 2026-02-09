from __future__ import annotations
from typing import List
from src.models.Report import Report
from src.models.ReportProject import ReportProject
from src.managers.ConfigManager import ConfigManager

class PortfolioReport:
    """
    Generates a portfolio from a report, intended for PDF export.
    This class leverages a Report object, which contains a list of
    curated ReportProject objects.
    """

    def __init__(self, report: Report, config_manager: ConfigManager):
        if not report.projects:
            raise ValueError("Cannot generate a portfolio from a report with no projects.")
        
        self.report = report
        self.config_manager = config_manager
        self._sort_projects()

    def _sort_projects(self):
        """Sorts projects based on the report's sort_by field."""
        if self.report.sort_by == "date_created":
            self.report.projects.sort(key=lambda p: p.date_created or datetime.min, reverse=True)
        elif self.report.sort_by == "last_modified":
            self.report.projects.sort(key=lambda p: p.last_modified or datetime.min, reverse=True)
        else: # Default to resume_score
            self.report.projects.sort(key=lambda p: p.resume_score, reverse=True)

    def generate_text_portfolio(self) -> str:
        """
        Generates a simple, text-based version of the full portfolio.
        This can be used for console output or as an intermediate representation.
        """
        full_text = []
        title = self.report.title or "Project Portfolio"
        full_text.append("=" * 80)
        full_text.append(title.upper().center(80))
        full_text.append("=" * 80)
        full_text.append("\n")

        for project in self.report.projects:
            if project.portfolio_entry:
                full_text.append(project.portfolio_entry)
                full_text.append("-" * 80)
                full_text.append("\n")

        return "\n".join(full_text)
