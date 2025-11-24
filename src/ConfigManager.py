from src.StorageManager import StorageManager
from typing import Any, Dict

class ConfigManager(StorageManager):
    """
    Manages configurations stored in the database.

    Each configuration item is stored as a key-value pair in the configs table.

    Values of complex data type are automatically serialized to JSON for storage and
    deserialized upon retrieval.
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

        key (str): The configuration key.

        value (Any): The value to store. Can be any JSON serializable type.
        """
        super().set({"key": key, "value": value})

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve a configuration value by key.

        key (str): The configuration key to look up.

        default (Any): Value to return if the key is not found. Defaults to None.

        Returns the deserialized value associated with the key, if found,
        or else default.
        """
        result = super().get(key, default)
        if result and isinstance(result, dict):
            return result.get("value")
        return default

    def get_all(self) -> Dict[str, Any]:
        """
        Retrieve all configuration items as a dictionary.

        Keys are mapped to their corresponding deserialized values.
        """
        rows = super().get_all()
        return {row["key"]: row["value"] for row in rows}
