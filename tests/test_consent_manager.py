import pytest
from src.ConsentManager import ConsentManager
from src.main import main

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

def test_request_consent_invalid_input(monkeypatch, tmp_path):
    cm = ConsentManager(db_path=str(tmp_path / "test.db"))
    monkeypatch.setattr("builtins.input", lambda _: "maybe")

    result = cm.request_consent()
    assert result is False
    assert cm.has_user_consented() is False

def test_case_sensitive_input_positive(monkeypatch, tmp_path):
    cm = ConsentManager(db_path=str(tmp_path / "test.db"))
    monkeypatch.setattr("builtins.input", lambda _: "YeS")

    result = cm.request_consent()
    assert result is True

def test_case_sensitive_input_negative(monkeypatch, tmp_path):
    cm = ConsentManager(db_path=str(tmp_path / "test.db"))
    monkeypatch.setattr("builtins.input", lambda _: "nO")

    result = cm.request_consent()
    assert result is False

def test_case_sensitive_input_invalid(monkeypatch, tmp_path):
    cm = ConsentManager(db_path=str(tmp_path / "test.db"))
    monkeypatch.setattr("builtins.input", lambda _: "MayBE")

    result = cm.request_consent()
    assert result is False

def test_corrupted_or_missing_consent(tmp_path):
    db = tmp_path / "test_config.db"
    cm = ConsentManager(db_path=str(db))

    with cm.manager._get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO configs (key, value) VALUES (?, ?)",
            ("user_consent", "}{broken json}")
        )
    assert cm.has_user_consented() is False
