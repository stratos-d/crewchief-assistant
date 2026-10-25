import os
import sys
import copy
import json
import threading
import time
from datetime import datetime
from dotenv import load_dotenv
from src import credentials
from src.constants import MAX_BUTTONS

# Load .env file if exists
load_dotenv()

# Resolve paths in the per-user application config directory
def _get_config_dir():
    if os.name == "nt":
        base_dir = os.environ.get("APPDATA") or os.path.expanduser("~\\AppData\\Roaming")
    elif sys.platform == "darwin":
        base_dir = os.path.expanduser("~/Library/Application Support")
    else:
        base_dir = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base_dir, "CrewChief Assistant")

CONFIG_PATH = os.path.join(_get_config_dir(), "config.json")
_client = None

# The voice engine thread reads settings while the UI thread saves them
_config_lock = threading.RLock()

DEFAULTS = {
    "settings": {
        "ptt_key": "scroll lock",
        "confidence_threshold": 50,
        "models": {
            "stt": "gpt-4o-mini-transcribe",
            "router": "gpt-4o-mini"
        },
        "audio": {
            "ptt_sound_enabled": True
        }
    },
    "controllers": [
        {
            "name": "Controller 1",
            "bindings": {
                str(i): {
                    "command": "radio check" if i == 1 else "",
                    "enabled": i == 1
                }
                for i in range(1, MAX_BUTTONS + 1)
            }
        }
    ]
}

def _deep_merge(base, overlay):
    """Deep merge overlay into base, preserving nested structures."""
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result

def load_config():
    with _config_lock:
        config = copy.deepcopy(DEFAULTS)
        loaded = _read_config_file()
        if loaded is None:
            save_config(config)
        else:
            config = _deep_merge(config, loaded)
        return config

def _read_config_file():
    """Read the saved config. Returns None if it is missing; an unreadable file is moved aside."""
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict):
            return loaded
    except ValueError:  # Covers JSONDecodeError and UnicodeDecodeError
        pass
    broken_path = CONFIG_PATH + f".broken_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.replace(CONFIG_PATH, broken_path)
    print(f"Config file was unreadable. Moved it to {broken_path} and restored defaults.")
    return None

def save_config(config):
    """Write the config atomically, so a crash mid-write can't leave a truncated file."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    tmp_path = CONFIG_PATH + ".tmp"
    with _config_lock:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        for attempt in range(5):
            try:
                os.replace(tmp_path, CONFIG_PATH)
                return
            except PermissionError:
                # On Windows another process (e.g. antivirus) can briefly hold the file open
                if attempt == 4:
                    raise
                time.sleep(0.05)

def get_setting(key_path, default=None):
    """Get a setting by dot-path like 'models.stt' or 'audio.input_device'."""
    config = load_config()
    keys = key_path.split(".")
    value = config.get("settings", {})
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value

def set_setting(key_path, value):
    """Set a setting by dot-path and save to config."""
    config = load_config()
    keys = key_path.split(".")
    target = config["settings"]
    for key in keys[:-1]:
        if key not in target:
            target[key] = {}
        target = target[key]
    target[keys[-1]] = value
    save_config(config)

def _parse_binding(value):
    """Normalize a binding value to {command, enabled}. Handles legacy string format."""
    if isinstance(value, dict):
        return value
    # Legacy: plain string
    cmd = value if isinstance(value, str) else ""
    return {"command": cmd, "enabled": bool(cmd)}

def get_controllers():
    """Get all controllers."""
    return load_config().get("controllers", [])

def get_all_commands():
    """Get all assigned+enabled commands across all controllers (for uniqueness validation)."""
    commands = []
    for controller in get_controllers():
        for v in controller.get("bindings", {}).values():
            b = _parse_binding(v)
            if b["command"] and b["enabled"]:
                commands.append(b["command"])
    return commands

def find_command_controller(command):
    """Find which controller and button has an enabled command. Returns (controller_index, button_key) or None."""
    if not command:
        return None
    for idx, controller in enumerate(get_controllers()):
        for button, value in controller.get("bindings", {}).items():
            b = _parse_binding(value)
            if b["enabled"] and b["command"] == command:
                return (idx, button)
    return None

def rename_binding(controller_index, button_key, new_command):
    """Rename a command for a button on a specific controller. Enables the button if a command is set."""
    config = load_config()
    controllers = config.get("controllers", [])
    if 0 <= controller_index < len(controllers):
        existing = _parse_binding(controllers[controller_index]["bindings"].get(button_key, {}))
        existing["command"] = new_command
        existing["enabled"] = bool(new_command)
        controllers[controller_index]["bindings"][button_key] = existing
        config["controllers"] = controllers
        save_config(config)
        return True
    return False

def get_api_key():
    key = credentials.read_api_key() or get_setting("openai_api_key", "")
    if key:
        return key
    return os.environ.get("OPENAI_API_KEY", "")

def save_api_key(api_key):
    global _client
    _client = None  # Invalidate cached client so new key takes effect
    if not credentials.available:
        set_setting("openai_api_key", api_key)
        return
    if api_key:
        credentials.write_api_key(api_key)
    else:
        credentials.delete_api_key()
    _remove_setting("openai_api_key")

def _remove_setting(key):
    with _config_lock:
        config = load_config()
        if config["settings"].pop(key, None) is not None:
            save_config(config)

def migrate_api_key():
    """Move a key that older versions saved in config.json into Windows Credential Manager."""
    key = get_setting("openai_api_key", "")
    if not key or not credentials.available:
        return
    try:
        credentials.write_api_key(key)
    except OSError as e:
        print(f"Couldn't move the API key to Windows Credential Manager: {e}")
        return
    _remove_setting("openai_api_key")
    print("Moved the OpenAI API key from config.json to Windows Credential Manager.")

def preload_openai():
    """Import the OpenAI SDK ahead of the first command. It takes over a second, so it isn't imported at startup."""
    import openai  # noqa: F401

def get_openai_client():
    global _client
    api_key = get_api_key()
    if not api_key:
        raise ValueError("OpenAI API key not configured. Set it in the GUI or as OPENAI_API_KEY environment variable.")
    if _client is None:
        import httpx
        from openai import OpenAI, DefaultHttpxClient
        # Keep idle connections for 60 s instead of httpx's 5 s, so nearby commands skip the TLS handshake
        _client = OpenAI(
            api_key=api_key,
            http_client=DefaultHttpxClient(limits=httpx.Limits(max_keepalive_connections=5, keepalive_expiry=60))
        )
    return _client

def warm_up_connection():
    """Open the HTTPS connection in the background while the driver is still talking."""
    def warm():
        try:
            get_openai_client().models.retrieve(get_setting("models.router", "gpt-4o-mini"))
        except Exception:
            pass  # Only an optimization; the real request reports any problem

    threading.Thread(target=warm, daemon=True).start()
