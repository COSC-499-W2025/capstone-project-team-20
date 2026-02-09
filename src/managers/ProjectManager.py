import sqlite3
import json
from typing import Any, Dict, Generator, Optional
from src.managers.StorageManager import StorageManager
from src.models.Project import Project


class ProjectManager(StorageManager):
    """Manages storage and retrieval of Project objects in the database."""
    def __init__(self, db_path="projects.db") -> None:
        super().__init__(db_path)

    @property
    def create_table_query(self) -> str:
        """
        Returns the SQL query to create the projects table.
        This schema should match the Project dataclass.
        """
        return """CREATE TABLE IF NOT EXISTS projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        file_path TEXT NOT NULL,
        root_folder TEXT,
        num_files INTEGER,
        size_kb INTEGER,
        author_count INTEGER,
        authors TEXT,
        author_contributions TEXT,
        languages TEXT,
        language_share TEXT,
        frameworks TEXT,
        skills_used TEXT,
        dependencies_list TEXT,
        dependency_files_list TEXT,
        build_tools TEXT,
        individual_contributions TEXT,
        collaboration_status TEXT,
        categories TEXT,
        total_loc INTEGER,
        comment_ratio REAL,
        test_file_ratio REAL,
        avg_functions_per_file REAL,
        max_function_length INTEGER,
        testing_discipline_level TEXT,
        testing_discipline_score REAL,
        documentation_habits_level TEXT,
        documentation_habits_score REAL,
        modularity_level TEXT,
        modularity_score REAL,
        language_depth_level TEXT,
        language_depth_score REAL,
        has_dockerfile TEXT,
        has_database TEXT,
        has_frontend TEXT,
        has_backend TEXT,
        has_test_files TEXT,
        has_readme TEXT,
        readme_keywords TEXT,
        bullets TEXT,
        summary TEXT,
        portfolio_details TEXT,
        resume_score REAL,
        date_created TEXT,
        last_modified TEXT,
        last_accessed TEXT
        )"""

    @property
    def table_name(self) -> str:
        return "projects"

    @property
    def primary_key(self) -> str:
        return "id"

    @property
    def columns(self) -> str:
        return (
            "id, name, file_path, root_folder, num_files, size_kb, author_count, "
            "authors, author_contributions, languages, language_share, frameworks, skills_used, "
            "dependencies_list, dependency_files_list, build_tools, "
            "individual_contributions, collaboration_status, categories, "
            "total_loc, comment_ratio, test_file_ratio, "
            "avg_functions_per_file, max_function_length, "
            "testing_discipline_level, testing_discipline_score, "
            "documentation_habits_level, documentation_habits_score, "
            "modularity_level, modularity_score, "
            "language_depth_level, language_depth_score, "
            "has_dockerfile, has_database, has_frontend, has_backend, "
            "has_test_files, has_readme, readme_keywords, "
            "bullets, summary, portfolio_details, resume_score, "
            "date_created, last_modified, last_accessed"
        )

    def set(self, proj: Project) -> None:
        project_dict = proj.to_dict()
        columns_to_set = self.columns_list
        if proj.id is None:
            # Don't try to insert 'id' for new records
            columns_to_set.remove('id')

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cols_str = ", ".join(columns_to_set)
            placeholders = ", ".join(f":{col}" for col in columns_to_set)

            # Create a dictionary of values for named placeholders
            values_dict = {col: project_dict.get(col) for col in columns_to_set}

            query = f"INSERT OR REPLACE INTO {self.table_name} ({cols_str}) VALUES ({placeholders})"
            cursor.execute(query, values_dict)

            if proj.id is None:
                proj.id = cursor.lastrowid

    def get(self, id: int) -> Optional[Project]:
        # Overrides the base 'get' to ensure correct deserialization
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = f"SELECT * FROM {self.table_name} WHERE id = ?"
            cursor.execute(query, (id,))
            result = cursor.fetchone()
            if result:
                return Project.from_dict(dict(result))
        return None


    def get_by_name(self, name: str) -> Optional[Project]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = f"SELECT * FROM {self.table_name} WHERE name = ?"
            cursor.execute(query, (name,))
            result = cursor.fetchone()
            if result:
                return Project.from_dict(dict(result))
        return None

    def get_all(self) -> Generator[Project, None, None]:
        for row in super().get_all():
            yield Project.from_dict(row)
