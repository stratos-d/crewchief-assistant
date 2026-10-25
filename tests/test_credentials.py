import json
import os

import pytest

from src import credentials
import src.config_manager as cm


def credential_store_usable():
    if not credentials.available:
        return False
    try:
        credentials.write_api_key("probe")
        credentials.delete_api_key()
        return True
    except OSError:  # e.g. a service account with no logon session
        return False


pytestmark = pytest.mark.skipif(not credential_store_usable(), reason="Windows Credential Manager not available")


def write_legacy_config(key):
    os.makedirs(os.path.dirname(cm.CONFIG_PATH), exist_ok=True)
    with open(cm.CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({"settings": {"ptt_key": "f8", "openai_api_key": key}}, f)


def test_write_read_overwrite_delete():
    assert credentials.read_api_key() == ""
    credentials.write_api_key("sk-test-one")
    assert credentials.read_api_key() == "sk-test-one"
    credentials.write_api_key("sk-test-two")
    assert credentials.read_api_key() == "sk-test-two"
    credentials.delete_api_key()
    assert credentials.read_api_key() == ""
    credentials.delete_api_key()  # deleting a missing entry is fine


def test_migration_moves_key_out_of_config():
    write_legacy_config("sk-legacy-123")
    cm.migrate_api_key()
    text = open(cm.CONFIG_PATH, encoding="utf-8").read()
    assert "openai_api_key" not in text and "sk-legacy" not in text
    assert json.loads(text)["settings"]["ptt_key"] == "f8"
    assert cm.get_api_key() == "sk-legacy-123"
    cm.migrate_api_key()  # second run is a no-op
    assert cm.get_api_key() == "sk-legacy-123"


def test_save_and_clear_never_touch_config():
    cm.save_api_key("sk-new-key")
    assert credentials.read_api_key() == "sk-new-key"
    assert "sk-new" not in open(cm.CONFIG_PATH, encoding="utf-8").read()
    cm.save_api_key("")
    assert credentials.read_api_key() == "" and cm.get_api_key() == ""


def test_environment_variable_fallback(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    assert cm.get_api_key() == "sk-from-env"
