import sqlite3
import json
from typing import Any, Dict
from src.managers.StorageManager import StorageManager

class ConfigManager(StorageManager):
    """
    Manages configurations stored in the database.
    Each configuration item is stored as a key-value pair in the configs table.
    """

    def __init__(self, db_path="config.db") -> None:
        super().__init__(db_path)

    @property
    def create_table_query(self) -> str:
        return "CREATE TABLE IF NOT EXISTS configs (key TEXT PRIMARY KEY, value TEXT)"

    @property
    def table_name(self) -> str:
        return "configs"

    @property
    def primary_key(self) -> str:
        return "key"

    @property
    def columns(self) -> str:
        return "key, value"

    def set(self, key: str, value: Any) -> None:
        """
        Store or update a configuration value by key.
        This method now implements its own database logic.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Serialize complex types to a JSON string for storage.
            serialized_value = json.dumps(value) if isinstance(value, (dict, list)) else value
            query = "INSERT OR REPLACE INTO configs (key, value) VALUES (?, ?)"
            cursor.execute(query, (key, serialized_value))

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a configuration value by key.
        This method now implements its own database logic.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT value FROM configs WHERE key = ?"
            cursor.execute(query, (key,))
            result = cursor.fetchone()
            if result:
                # The value is a tuple, e.g., ('["mr-sban"]',)
                # We need to deserialize it from JSON.
                try:
                    return json.loads(result[0])
                except (json.JSONDecodeError, TypeError):
                    return result[0] # Return as is if not valid JSON
        return default

    def get_all(self) -> Dict[str, Any]:
        """
        Retrieve all configuration items as a dictionary.
        This method now implements its own database logic.
        """
        configs = {}
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT key, value FROM configs"
            cursor.execute(query)
            for row in cursor.fetchall():
                key, value = row
                try:
                    configs[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    configs[key] = value
        return configs
