import sqlite3
from contextlib import contextmanager

# TODO: Decide on whether we use config.db or a more general database here
# TODO: Look at making this Singleton
# TODO: ensure contextmanager connection handling works as intended
# TODO: implement set(), get(), get_all(), delete(), clear()
# TODO: verify SQLite table initialization works as intended

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
            cursor.execute("""
            INSERT OR REPLACE INTO configs (key, value)
            VALUES (?, ?)
            """, (key, str(value)))

    def get(self, key, default=None):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT value FROM configs WHERE key = ?
            """, (key,))
            result = cursor.fetchone()
            return result[0] if result else default

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
            config_dict = {key: value for key, value in results}
            return config_dict

    def clear(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            DELETE FROM configs
            """)

            
