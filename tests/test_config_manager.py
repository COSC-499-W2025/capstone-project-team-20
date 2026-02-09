import pytest
import os
from src.managers.ConfigManager import ConfigManager

@pytest.fixture
def manager():
    """Create a ConfigManager with a test database, and clean up after."""
    test_db = "test_config.db"
    if os.path.exists(test_db):
        os.remove(test_db)
    manager = ConfigManager(db_path=test_db)
    yield manager
    if os.path.exists(test_db):
        os.remove(test_db)

def test_set_and_get_string(manager: ConfigManager):
    manager.set("name", "Alice")
    assert manager.get("name") == "Alice"

def test_set_and_get_list(manager: ConfigManager):
    """Tests storing and retrieving a list, which should be JSON serialized."""
    usernames = ["user1", "user2"]
    manager.set("usernames", usernames)
    assert manager.get("usernames") == usernames

def test_set_and_get_dict(manager: ConfigManager):
    """Tests storing and retrieving a dictionary."""
    settings = {"theme": "dark", "notifications": True}
    manager.set("settings", settings)
    assert manager.get("settings") == settings

def test_update_existing_value(manager: ConfigManager):
    manager.set("key", "old_value")
    manager.set("key", "new_value")
    assert manager.get("key") == "new_value"

def test_get_nonexistent_key(manager: ConfigManager):
    """Getting a nonexistent key should return the default value (None)."""
    assert manager.get("nonexistent_key") is None

def test_get_nonexistent_key_with_default(manager: ConfigManager):
    """Getting a nonexistent key should return the specified default value."""
    assert manager.get("nonexistent_key", default="fallback") == "fallback"

def test_get_all(manager: ConfigManager):
    manager.set("name", "Bob")
    manager.set("roles", ["admin", "editor"])

    all_configs = manager.get_all()

    assert len(all_configs) == 2
    assert all_configs["name"] == "Bob"
    assert all_configs["roles"] == ["admin", "editor"]

def test_persistence_across_instances(manager: ConfigManager):
    """Tests that data persists between different ConfigManager instances."""
    db_path = manager.db_path
    manager.set("persistent_key", "persistent_value")

    # Create a new manager instance connected to the same database file
    new_manager = ConfigManager(db_path=db_path)
    assert new_manager.get("persistent_key") == "persistent_value"

def test_get_all_on_empty_db(manager: ConfigManager):
    """get_all on a new/empty database should return an empty dictionary."""
    assert manager.get_all() == {}
