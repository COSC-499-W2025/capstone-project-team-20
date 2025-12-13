import pytest
import os
from src.managers.ConfigManager import ConfigManager

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

# Tests for new delete() method
def test_delete_existing_key(config_manager):
    config_manager.set("temp_key", "temp_value")
    assert config_manager.get("temp_key") == "temp_value"
    config_manager.delete("temp_key")
    assert config_manager.get("temp_key") is None

def test_delete_nonexistent_key_no_error(config_manager):
    """Deleting a nonexistent key should not raise an error"""
    config_manager.delete("does_not_exist")
    assert config_manager.get("does_not_exist") is None

def test_delete_persists_across_instances(config_manager):
    db_path = config_manager.db_path
    config_manager.set("to_delete", "value")
    config_manager.delete("to_delete")
    new_manager = ConfigManager(db_path=db_path)
    assert new_manager.get("to_delete") is None

# Tests for new clear() method
def test_clear_removes_all_entries(config_manager):
    config_manager.set("key1", "value1")
    config_manager.set("key2", 42)
    config_manager.set("key3", ["list", "data"])
    config_manager.clear()
    assert config_manager.get_all() == {}
    assert config_manager.get("key1") is None
    assert config_manager.get("key2") is None
    assert config_manager.get("key3") is None

def test_clear_on_empty_database(config_manager):
    """Clearing an already empty database should not cause errors"""
    config_manager.clear()
    assert config_manager.get_all() == {}

def test_clear_persists_across_instances(config_manager):
    db_path = config_manager.db_path
    config_manager.set("data", "value")
    config_manager.clear()
    new_manager = ConfigManager(db_path=db_path)
    assert new_manager.get_all() == {}

# Tests for username-specific configuration
def test_set_and_get_usernames_list(config_manager):
    usernames = ["Alice", "Bob", "Charlie"]
    config_manager.set("usernames", usernames)
    assert config_manager.get("usernames") == usernames

def test_delete_usernames_key(config_manager):
    config_manager.set("usernames", ["Alice", "Bob"])
    config_manager.delete("usernames")
    assert config_manager.get("usernames") is None
