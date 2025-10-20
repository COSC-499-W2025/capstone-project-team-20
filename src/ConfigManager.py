from src.StorageManager import StorageManager

class ConfigManager(StorageManager):

    def __init__(self, db_path="config.db") -> None:
        super().__init__(db_path)

    _create_table_query = """ CREATE TABLE IF NOT EXISTS configs (key TEXT PRIMARY KEY,value TEXT NOT NULL)"""
    _set_value_query = """INSERT OR REPLACE INTO configs (key, value) VALUES (?, ?)"""
    _get_value_query = """SELECT value FROM configs WHERE key = ?"""
    _get_all_query = """SELECT key, value FROM configs"""
    _delete_value_query = """DELETE FROM configs WHERE key = ?"""
    _clear_query = """DELETE FROM configs"""
    
    @property
    def create_table_query(self) -> str:
        return self._create_table_query
    
    @property
    def set_value_query(self) -> str:
        return self._set_value_query
    
    @property
    def get_value_query(self) -> str:
        return self._get_value_query
    
    @property
    def get_all_query(self) -> str:
        return self._get_all_query
    
    @property
    def delete_value_query(self) -> str:
        return self._delete_value_query
    
    @property
    def clear_query(self) -> str:
        return self._clear_query
