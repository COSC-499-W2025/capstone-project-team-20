import sqlite3
import json
from contextlib import contextmanager

class ConfigManager: 
    def __init__(self, db_path="config.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(""" 
            CREATE TABLE IF NOT EXISTS configs (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL)
                """)

    def set(self, key, value):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            serialized_value = json.dumps(value)
            cursor.execute("""
            INSERT OR REPLACE INTO configs (key, value)
            VALUES (?, ?)
            """, (key, serialized_value))

    def get(self, key, default=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT value FROM configs WHERE key = ?
            """, (key,))
            result = cursor.fetchone()
            if result:
                try: 
                    return json.loads(result[0])
                except json.JSONDecodeError:
                    return default
            return default

    def delete(self, key):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            DELETE FROM configs WHERE key = ?
            """, (key,))
    
    def get_all(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT key, value FROM configs
            """)
            results = cursor.fetchall()
            config_dict = {}
            for key, value in results:
                try:
                    config_dict[key] = json.loads(value)
                except json.JSONDecodeError:
                    config_dict[key] = value
            return config_dict

    def clear(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            DELETE FROM configs
            """)
