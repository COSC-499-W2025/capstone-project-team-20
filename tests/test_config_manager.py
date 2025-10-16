import pytest
import os
from src.ConfigManager import ConfigManager

@pytest.fixture
def config_manager():
    """Create a ConfigManager with test database, cleanup after."""
    test_db = "test_config.db"
    manager = ConfigManager(db_path=test_db)
    yield manager
    if os.path.exists(test_db):
        os.remove(test_db)


# Positive Test Cases


def test_set_and_get_basic_types(config_manager):
    config_manager.set("name", "Alice")
    config_manager.set("enabled", True)
    config_manager.set("count", 42)
    assert config_manager.get("name") == "Alice"
    assert config_manager.get("enabled") is True
    assert config_manager.get("count") == 42

def test_set_and_get_complex_types(config_manager):
    config_manager.set("list", [1, 2, 3, "four"])
    config_manager.set("dict", {"nested": {"key": "value"}})
    config_manager.set("mixed", {"list": [1, 2], "bool": True, "null": None})
    assert config_manager.get("list") == [1, 2, 3, "four"]
    assert config_manager.get("dict") == {"nested": {"key": "value"}}
    assert config_manager.get("mixed") == {"list": [1, 2], "bool": True, "null": None}

def test_set_and_get_none(config_manager):
    config_manager.set("null_value", None)
    assert config_manager.get("null_value") is None

def test_set_and_get_empty_collections(config_manager):
    config_manager.set("empty_list", [])
    config_manager.set("empty_dict", {})
    config_manager.set("empty_string", "") 
    assert config_manager.get("empty_list") == []
    assert config_manager.get("empty_dict") == {}
    assert config_manager.get("empty_string") == ""

def test_update_existing_value(config_manager):
    config_manager.set("value", "old")
    config_manager.set("value", "new")
    assert config_manager.get("value") == "new"

def test_delete(config_manager):
    config_manager.set("temp", "data")
    config_manager.delete("temp")
    assert config_manager.get("temp") is None

def test_delete_nonexistent_key(config_manager):
    config_manager.delete("nonexistent")
    assert config_manager.get("nonexistent") is None

def test_get_all(config_manager):
    config_manager.set("key1", "value1")
    config_manager.set("key2", 42)
    all_configs = config_manager.get_all()
    assert all_configs == {"key1": "value1", "key2": 42}

def test_clear(config_manager):
    config_manager.set("key", "value")
    config_manager.clear()
    assert config_manager.get_all() == {}

def test_persistence_across_instances(config_manager):
    db_path = config_manager.db_path
    config_manager.set("persistent", "data")
    new_manager = ConfigManager(db_path=db_path)
    assert new_manager.get("persistent") == "data"


# Negative Test Cases


def test_corrupted_json_returns_default(config_manager):
    with config_manager._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO configs (key, value) VALUES (?, ?)",
            ("corrupted", "not valid json{{{")
        )
    assert config_manager.get("corrupted") is None
    assert config_manager.get("corrupted", default="fallback") == "fallback"

def test_get_nonexistent_key_with_default(config_manager):
    assert config_manager.get("missing") is None
    assert config_manager.get("missing", default="fallback") == "fallback"

def test_get_all_with_corrupted_entry(config_manager):
    config_manager.set("valid", {"key": "value", "count": 42})
    with config_manager._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO configs (key, value) VALUES (?, ?)",
            ("corrupted", "}{invalid json")
        )
    all_configs = config_manager.get_all()
    assert all_configs["valid"] == {"key": "value", "count": 42}
    assert all_configs["corrupted"] == "}{invalid json"