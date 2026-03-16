from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple
import sqlite3

from src.managers.StorageManager import StorageManager


class FileHashManager(StorageManager):
    """Tracks unique file hashes across uploads to avoid duplicate storage."""

    def __init__(self, db_path: str = "projects.db") -> None:
        super().__init__(db_path)
        self._cache: set = self._load_all_hashes()

    def _load_all_hashes(self) -> set:
        """Load all known hashes from DB into memory once at startup."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT file_hash FROM {self.table_name}")
            return {row[0] for row in cursor.fetchall()}

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
        """O(1) in-memory lookup."""
        return file_hash in self._cache

    def register_hash(
        self,
        file_hash: str,
        file_path: str,
        project_name: str,
        seen_at: Optional[datetime] = None,
    ) -> bool:
        """Register a single hash; returns True if new, False if already known."""
        if file_hash in self._cache:
            return False
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
                self._cache.add(file_hash)
                return True
        return False

    def register_hashes_batch(
        self,
        entries: List[Tuple[str, str, str]],
        seen_at: Optional[datetime] = None,
    ) -> Dict[str, int]:
        """
        Register multiple hashes in a single DB transaction.
        entries: list of (file_hash, file_path, project_name)
        Returns {"new": int, "duplicate": int}
        """
        timestamp = (seen_at or datetime.now()).isoformat()
        new_count = 0
        duplicate_count = 0

        new_entries = []
        for file_hash, file_path, project_name in entries:
            if file_hash in self._cache:
                duplicate_count += 1
            else:
                new_entries.append((file_hash, file_path, project_name, timestamp))
                self._cache.add(file_hash)
                new_count += 1

        if new_entries:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany(
                    f"""INSERT OR IGNORE INTO {self.table_name}
                    (file_hash, file_path, project_name, last_seen)
                    VALUES (?, ?, ?, ?)""",
                    new_entries,
                )

        return {"new": new_count, "duplicate": duplicate_count}

    def get_all(self) -> Generator[Dict[str, Any], None, None]:
        return super().get_all()
