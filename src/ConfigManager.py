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
                value TEXT NOT NULL
                )
                """)
