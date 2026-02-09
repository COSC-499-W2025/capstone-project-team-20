import sqlite3
import json
from contextlib import contextmanager
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator

class StorageManager(ABC):
    """
    Abstract base class for handling database reads and writes.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(self.create_table_query)

    def _deserialize_row(self, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Unpack any complex data types from serialized JSON back to its original form."""
        if not row_dict:
            return {}
        deserialized = {}
        for col, val in row_dict.items():
            try:
                if isinstance(val, str):
                    deserialized[col] = json.loads(val)
                else:
                    deserialized[col] = val
            except (json.JSONDecodeError, TypeError):
                deserialized[col] = val
        return deserialized

    def _retrieve_id(self, cursor: sqlite3.Cursor, row: Dict[str, Any]) -> None:
        pass

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @property
    def columns_list(self) -> list[str]:
        return [c.strip() for c in self.columns.split(",")]

    @property
    def placeholders(self) -> str:
        return ", ".join("?" for _ in self.columns_list)

    @property
    @abstractmethod
    def create_table_query(self) -> str:
        pass

    @property
    @abstractmethod
    def table_name(self) -> str:
        pass

    @property
    @abstractmethod
    def primary_key(self) -> str:
        pass

    @property
    @abstractmethod
    def columns(self) -> str:
        pass

    def get(self, key: int, default: Any = None) -> Dict[str, Any]:
        """
        Retrieve a row by an INTEGER primary key.
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row # Use row_factory for easy dict conversion
            cursor = conn.cursor()
            query = f"SELECT * FROM {self.table_name} WHERE {self.primary_key} = ?"
            cursor.execute(query, (key,))
            result = cursor.fetchone()
            if result:
                # The _deserialize_row is now redundant if models handle it, but good for safety
                return self._deserialize_row(dict(result))
        return default

    def get_all(self) -> Generator[Dict[str, Any], None, None]:
        """
        Retrieve all rows from a table as a Generator.
        """
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            query = f"SELECT * FROM {self.table_name}"
            cursor.execute(query)
            for row in cursor.fetchall():
                yield self._deserialize_row(dict(row))

    def clear(self) -> None:
        """Delete all rows from a table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"DELETE FROM {self.table_name}"
            cursor.execute(query)
