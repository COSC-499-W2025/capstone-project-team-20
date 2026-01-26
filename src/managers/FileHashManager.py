from datetime import datetime
from typing import Any, Dict, Generator, Optional
import sqlite3

from src.managers.StorageManager import StorageManager


class FileHashManager(StorageManager):
    """Tracks unique file hashes across uploads to avoid duplicate storage."""

    def __init__(self, db_path: str = "projects.db") -> None:
        super().__init__(db_path)

    @property
    def create_table_query(self) -> str:
        return """CREATE TABLE IF NOT EXISTS file_hashes (
        file_hash TEXT PRIMARY KEY,
        file_path TEXT,
        project_name TEXT,
        last_seen TEXT
        )"""

    @property
    def table_name(self) -> str:
        return "file_hashes"

    @property
    def primary_key(self) -> str:
        return "file_hash"

    @property
    def columns(self) -> str:
        return "file_hash, file_path, project_name, last_seen"

    def has_hash(self, file_hash: str) -> bool:
        return self.get(file_hash) is not None

    def register_hash(
        self,
        file_hash: str,
        file_path: str,
        project_name: str,
        seen_at: Optional[datetime] = None,
    ) -> bool:
        """Register a hash; returns True if new, False if already known."""
        timestamp = (seen_at or datetime.now()).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"""INSERT OR IGNORE INTO {self.table_name}
                (file_hash, file_path, project_name, last_seen)
                VALUES (?, ?, ?, ?)""",
                (file_hash, file_path, project_name, timestamp),
            )
            if cursor.rowcount > 0:
                return True
            cursor.execute(
                f"UPDATE {self.table_name} SET last_seen = ? WHERE file_hash = ?",
                (timestamp, file_hash),
            )
        return False

    def get_all(self) -> Generator[Dict[str, Any], None, None]:
        return super().get_all()