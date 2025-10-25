import sqlite3
import json
from contextlib import contextmanager
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator

class StorageManager(ABC): 
    """
    Abstract base class for handling database reads and writes.
    
    Defines: set, get, get_all, delete, clear.

    Child classes need to define their table schema and structure, and optionally, override set, get and get_all in order to unpack the return types of it’s base class. (For example, StorageManager’s set() method expects a dict.

    All complex data types (dict, list, bool) are automatically serialized to JSON for storage and deserialized upon retrieval.
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
        for col, val in row_dict.items():
            try:
                row_dict[col] = json.loads(val)
            except (json.JSONDecodeError, TypeError):
                row_dict[col] = val
        return row_dict

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Manages the setup and cleanup for database reads and writes.

        Returns a Generator object, ensuring that only one connection is open at once.
        """
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @property
    def columns_list(self) -> list[str]:
        """Return a list of all columns a table has for use in SQL queries."""
        return [c.strip() for c in self.columns.split(",")]

    @property
    def placeholders(self) -> str:
        """Return a string of '?' placeholders for use in SQL queries."""
        return ", ".join("?" for _ in self.columns_list)


    # the @property and @abstractmethod combination forces child classes to define an attribute

    @property
    @abstractmethod
    def create_table_query(self) -> str:
        """Return the create table query for a table for use in SQL queries."""
        pass

    @property
    @abstractmethod
    def table_name(self) -> str:
        """Return the table name of a table for use in SQL queries."""
        pass

    @property
    @abstractmethod
    def primary_key(self) -> str:
        """Return the primary key of a table for use in SQL queries."""
        pass
    
    @property
    @abstractmethod
    def columns(self) -> str:
        """Return an ordered string of all columns a table has for use in SQL queries."""
        pass

    def set(self, row: Dict[str, Any]) -> None:
        """
        Insert or update a row, expects a dictionary with column names as keys and values to store. 

        Key-value pairs must be set in the order defined in the child class’s columns property.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            values = [row[i] for i in self.columns_list]
            serialized_values = [
            json.dumps(v) if isinstance(v, (dict, list, bool)) else v
            for v in values
            ]
            query = f"INSERT OR REPLACE INTO {self.table_name} ({self.columns}) VALUES ({self.placeholders})"
            cursor.execute(query, serialized_values)
        
    def get(self, key: str, default: Any = None) -> Dict[str, Any]:
        """
        Retrieve a row by primary key.
        
        default is an optional fallback value to be used if the key doesn't exist. Defaults to None.
        """

        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"SELECT {self.columns} FROM {self.table_name} WHERE {self.primary_key} = ?"
            cursor.execute(query, (key,))
            result = cursor.fetchone()
            if result:
                row_dict = dict(zip(self.columns_list, result))
                return self._deserialize_row(row_dict)
        return default
    
    def delete(self, key: str) -> bool:
        """ 
        Delete a row associated with a primary key value from the database.

        Returns `True` if the delete operation is successful.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"DELETE FROM {self.table_name} WHERE {self.primary_key} = ?"
            cursor.execute(query, (key,))
            return cursor.rowcount > 0
    
    def get_all(self) -> list[Dict[str, Any]]:
        """
        Retrieve all rows from a table.

        Rows are returned as a list of dicts with deserialized values.
        """
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
        """
        Delete all rows from a table.

        Use with caution.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            query = f"DELETE FROM {self.table_name}"
            cursor.execute(query)