import sqlite3
import json
from contextlib import contextmanager
from abc import ABC, abstractmethod
from typing import Any
from typing import Generator
from typing import Dict

class StorageManager(ABC): 

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(self.create_table_query)

    # handles the setup and cleanup for database writes and reads
    # returns a Generator object, ensuring that only one connection is open at once

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @property
    def columns_list(self) -> list[str]:
        return [c.strip() for c in self.columns.split(",")]
    
    # returns a string of ? placeholders for use in SQL queries

    @property
    def placeholders(self) -> str:
           return ", ".join("?" for _ in self.columns_list)


    # the @property and @abstractmethod combination forces child classes to define an attribute

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

    def set(self, data: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            values = [data[i] for i in self.columns_list]
            # serialize any values of complex data type
            serialized_values = [
            json.dumps(v) if isinstance(v, (dict, list, bool)) else v
            for v in values
            ]
            query = f"INSERT OR REPLACE INTO {self.table_name} ({self.columns}) VALUES ({self.placeholders})"
            cursor.execute(query, serialized_values)
                
    # default param can be used as a fallback, in case the value you're looking for doesn't exist
        
    def get(self, key: str, default: Any = None) -> Dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"SELECT {self.columns} FROM {self.table_name} WHERE {self.primary_key} = ?"
            cursor.execute(query, (key,))
            result = cursor.fetchone()
            if result:
                row_dict = dict(zip(self.columns_list, result))
                for col, val in row_dict.items():
                    # deserialize any values that need it
                    try:
                        row_dict[col] = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        row_dict[col] = val
                return row_dict
        return default

    def delete(self, key: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"DELETE FROM {self.table_name} WHERE {self.primary_key} = ?"
            cursor.execute(query, (key,))
    
    def get_all(self) -> list[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"SELECT {self.columns} FROM {self.table_name}"
            cursor.execute(query)
            results = cursor.fetchall()
            all_rows = []
            for row in results:
                # deserialize any values that need it
                row_dict = dict(zip(self.columns_list, row))
                for col, val in row_dict.items():
                    try:
                        row_dict[col] = json.loads(val)
                    except (json.JSONDecodeError, TypeError):
                        row_dict[col] = val
                all_rows.append(row_dict)
        return all_rows

    def clear(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"DELETE FROM {self.table_name}"
            cursor.execute(query)