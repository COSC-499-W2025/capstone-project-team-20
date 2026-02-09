import sqlite3
import json
from typing import Any, Dict, List, Optional
from src.managers.StorageManager import StorageManager
from src.models.Report import Report
from src.models.ReportProject import ReportProject

class ReportManager(StorageManager):
    """Manages storage and retrieval of Report objects, coordinating with ReportProjectManager."""

    def __init__(self, db_path="reports.db") -> None:
        super().__init__(db_path)
        with self._get_connection() as conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS report_projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_id INTEGER NOT NULL,
                project_name TEXT NOT NULL,
                resume_score REAL DEFAULT 0.0,
                bullets TEXT,
                summary TEXT,
                portfolio_details TEXT, -- ADDED THIS MISSING FIELD
                languages TEXT,
                language_share TEXT,
                frameworks TEXT,
                date_created TEXT,
                last_modified TEXT,
                collaboration_status TEXT DEFAULT 'individual',
                FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
            )""")

    @property
    def table_name(self) -> str:
        return "reports"

    @property
    def primary_key(self) -> str:
        return "id"

    @property
    def create_table_query(self) -> str:
        return """CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            created_at TEXT,
            sort_by TEXT,
            notes TEXT
        )"""

    @property
    def columns(self) -> str:
        return "id, title, created_at, sort_by, notes"

    def create_report(self, report: Report) -> Optional[Report]:
        """Saves a report and its associated projects to the database."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                report_query = "INSERT INTO reports (title, created_at, sort_by, notes) VALUES (?, ?, ?, ?)"
                values = (report.title, report.created_at.isoformat(), report.sort_by, report.notes)
                cursor.execute(report_query, values)
                report.id = cursor.lastrowid

                for proj in report.projects:
                    self.set_from_report_project(report.id, proj, conn)

                return report
            except sqlite3.Error as e:
                print(f"Database error in create_report: {e}")
                return None

    def set_from_report_project(self, report_id: int, report_project: ReportProject, conn: sqlite3.Connection) -> None:
        """Stores a single ReportProject using the provided connection."""
        # --- THIS IS THE FIX ---
        # Added portfolio_details to the data being saved.
        row = {
            "report_id": report_id,
            "project_name": report_project.project_name,
            "resume_score": report_project.resume_score,
            "bullets": json.dumps(report_project.bullets),
            "summary": report_project.summary,
            "portfolio_details": json.dumps(report_project.portfolio_details.to_dict()),
            "languages": json.dumps(report_project.languages),
            "language_share": json.dumps(report_project.language_share),
            "frameworks": json.dumps(report_project.frameworks),
            "date_created": report_project.date_created.isoformat() if report_project.date_created else None,
            "last_modified": report_project.last_modified.isoformat() if report_project.last_modified else None,
            "collaboration_status": report_project.collaboration_status,
        }

        columns = ", ".join(row.keys())
        placeholders = ", ".join("?" for _ in row)
        query = f"INSERT INTO report_projects ({columns}) VALUES ({placeholders})"
        values = list(row.values())
        conn.execute(query, values)

    def get_report(self, report_id: int) -> Optional[Report]:
        """Retrieves a single report and populates it with its projects."""
        row_dict = self.get(report_id)
        if not row_dict:
            return None

        report = Report.from_dict(row_dict)

        with self._get_connection() as conn:
            report.projects = self._get_all_for_report_conn(report.id, conn)

        return report

    def _get_all_for_report_conn(self, report_id: int, conn: sqlite3.Connection) -> List[ReportProject]:
        """Retrieves all projects for a report using an existing connection."""
        projects = []
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = "SELECT * FROM report_projects WHERE report_id = ? ORDER BY id"
        cursor.execute(query, (report_id,))

        for row in cursor.fetchall():
            projects.append(ReportProject.from_dict(dict(row)))
        return projects

    def list_reports(self) -> List[Report]:
        """Returns a list of all saved reports, each populated with their projects."""
        reports = []
        for row_dict in self.get_all():
            report = Report.from_dict(row_dict)
            if report and report.id is not None:
                with self._get_connection() as conn:
                    report.projects = self._get_all_for_report_conn(report.id, conn)
            reports.append(report)
        return reports
