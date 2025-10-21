from src.StorageManager import StorageManager
from typing import Any
from typing import Dict

class ConfigManager(StorageManager):

    def __init__(self, db_path="config.db") -> None:
        super().__init__(db_path)

    @property
    def create_table_query(self) -> str:
        return "CREATE TABLE IF NOT EXISTS configs (key TEXT PRIMARY KEY,value TEXT)"

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
        super().set({"key": key, "value": value})
    
    def get(self, key: str, default: Any = None) -> Any:
        result = super().get(key, default)
        if result and isinstance(result, dict):
            return result.get("value", default)
        return default
    
    def get_all(self) -> Dict[str, Any]:
        rows = super().get_all()
        return {row["key"]: row["value"] for row in rows}