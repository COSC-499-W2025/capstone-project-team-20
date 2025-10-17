import pytest
from src.ConsentManager import ConsentManager
from src.main import main

def test_main_runs(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "yes")
    main()
    assert True

@pytest.fixture
def consent(tmp_path):
    db_path = tmp_path / "test_config.db"
    return ConsentManager(db_path=str(db_path))

def test_initial_consent_is_false(consent):
    assert consent.has_user_consented() is False

def test_set_and_check_consent(consent):
    consent.manager.set("user_consent", True)
    assert consent.has_user_consented() is True

def test_persistence_across_interfaces(tmp_path):
    db_path = tmp_path / "test_config.db"
    cm1 = ConsentManager(db_path=str(db_path))
    cm1.manager.set("user_consent", True)
    
    cm2 = ConsentManager(db_path=str(db_path))
    assert cm2.has_user_consented() is True