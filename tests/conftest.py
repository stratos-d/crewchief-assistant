"""Test isolation: a scratch settings folder, a test Credential Manager entry, no sounds, no real API key.

Runs locally and on GitHub's Windows runners (which have no vJoy driver and no microphone).
"""
import os
import sys
import tempfile
import types

# Must happen before anything imports src.config_manager, which reads these at import time
os.environ["APPDATA"] = tempfile.mkdtemp(prefix="crewchief_tests_")
os.environ["OPENAI_API_KEY"] = ""  # load_dotenv won't override it, so a developer's .env key stays unused

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pyvjoy  # noqa: F401
except BaseException:  # pyvjoy calls sys.exit() when its DLL can't load
    stub = types.ModuleType("pyvjoy")
    stub.VJoyDevice = None
    sys.modules["pyvjoy"] = stub

import pytest  # noqa: E402

from src import credentials  # noqa: E402
import src.config_manager as cm  # noqa: E402
import src.sounds as sounds  # noqa: E402

credentials.TARGET = "CrewChief Assistant PYTEST"


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    """Fresh config file, no stored key and no beeps for every test."""
    if os.path.exists(cm.CONFIG_PATH):
        os.remove(cm.CONFIG_PATH)
    monkeypatch.setattr(sounds, "_play_sound", lambda path: None)
    yield
    try:
        credentials.delete_api_key()
    except OSError:
        pass
