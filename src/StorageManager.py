import sqlite3
import json
from contextlib import contextmanager
from abc import ABC, abstractmethod
from typing import Any
from typing import Generator

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

    # the @property and @abstractmethod combination forces child classes to define an attribute

    @property
    @abstractmethod
    def create_table_query(self) -> str:
        pass
    
    @property
    @abstractmethod
    def set_value_query(self) -> str:
        pass
    
    @property
    @abstractmethod
    def get_value_query(self) -> str:
        pass
    
    @property
    @abstractmethod
    def get_all_query(self) -> str:
        pass
    
    @property
    @abstractmethod
    def delete_value_query(self) -> str:
        pass
    
    @property
    @abstractmethod
    def clear_query(self) -> str:
        pass

    def set(self, key: str, value: Any) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            serialized_value = json.dumps(value)
            cursor.execute(self.set_value_query, (key, serialized_value))

    # default param can be used as a fallback, in case the value you're looking for doesn't exist

    def get(self, key: str, default: Any = None) -> Any:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(self.get_value_query, (key,))
            result = cursor.fetchone()
            if result:
                try: 
                    return json.loads(result[0])
                except json.JSONDecodeError:
                    return default
            return default

    def delete(self, key: str) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(self.delete_value_query, (key,))
    
    def get_all(self) -> dict[str, Any]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(self.get_all_query)
            results = cursor.fetchall()
            value_dict = {}
            for key, value in results:
                try:
                    value_dict[key] = json.loads(value)
                except json.JSONDecodeError:
                    value_dict[key] = value
            return value_dict

    def clear(self) -> None:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(self.clear_query)