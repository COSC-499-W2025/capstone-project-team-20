import sqlite3
import json
from contextlib import contextmanager
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator

class StorageManager(ABC): 

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(self.create_table_query)

    def _deserialize_row(self, row_dict: Dict[str, Any]) -> Dict[str, Any]:
        for col, val in row_dict.items():
            try:
                row_dict[col] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                row_dict[col] = val
        return row_dict

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

    def set(self, row: Dict[str, Any]) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            values = [row[i] for i in self.columns_list]
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
                return self._deserialize_row(row_dict)
        return default

    #returns true if delete was successful
    
    def delete(self, key: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"DELETE FROM {self.table_name} WHERE {self.primary_key} = ?"
            cursor.execute(query, (key,))
            return cursor.rowcount > 0
    
    def get_all(self) -> list[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"SELECT {self.columns} FROM {self.table_name}"
            cursor.execute(query)
            results = cursor.fetchall()
            all_rows = []
            for row in results:
                row_dict = dict(zip(self.columns_list, row))
                all_rows.append(self._deserialize_row(row_dict))
        return all_rows

    def clear(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"DELETE FROM {self.table_name}"
            cursor.execute(query)