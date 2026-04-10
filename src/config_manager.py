import os
import sys
import json
import shutil
from dotenv import load_dotenv
from openai import OpenAI

# Load .env file if exists
load_dotenv()

# Resolve paths relative to the executable/script location
if getattr(sys, 'frozen', False):
    _BASE_DIR = os.path.dirname(sys.executable)
else:
    _BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(_BASE_DIR, "config.json")
_DEFAULT_CONFIG_PATH = os.path.join(_BASE_DIR, "config.default.json")
_client = None

DEFAULTS = {
    "settings": {
        "ptt_key": "scroll lock",
        "openai_api_key": "",
        "confidence_threshold": 50,
        "models": {
            "stt": "whisper-1",
            "router": "gpt-4o-mini"
        },
        "audio": {
            "sample_rate": 44100,
            "ptt_sound_enabled": True
        }
    },
    "controllers": [
        {"name": "Controller 1", "bindings": {}}
    ],
    "available_buttons": [
        "A", "B", "X", "Y",
        "DPAD_UP", "DPAD_DOWN", "DPAD_LEFT", "DPAD_RIGHT",
        "LEFT_SHOULDER", "RIGHT_SHOULDER",
        "LEFT_THUMB", "RIGHT_THUMB",
        "BACK", "START"
    ]
}

DEFAULT_THEME = {
    "bg_color": "#0f1113",
    "card_bg": "#1c1f23",
    "accent_color": "#00e5ff",
    "text_main": "#f8f9fa",
    "text_dim": "#94a3b8",
    "ready_green": "#00c853",
    "stop_red": "#ff1744",
    "proc_orange": "#ff9100",
    "btn_bg": "#2d3436",
    "term_bg": "#000000"
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
    config = _deep_merge(DEFAULTS, {})
    if not os.path.exists(CONFIG_PATH):
        # Copy default config on first run
        if os.path.exists(_DEFAULT_CONFIG_PATH):
            shutil.copy2(_DEFAULT_CONFIG_PATH, CONFIG_PATH)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            loaded = json.load(f)
            config = _deep_merge(config, loaded)
    return config

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

def get_setting(key_path, default=None):
    """Get a setting by dot-path like 'models.stt' or 'audio.sample_rate'."""
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

def get_controllers():
    """Get all controllers."""
    return load_config().get("controllers", [])

def get_controller_bindings(controller_index):
    """Get bindings for a specific controller."""
    controllers = get_controllers()
    if 0 <= controller_index < len(controllers):
        return controllers[controller_index].get("bindings", {})
    return {}

def get_all_commands():
    """Get all commands across all controllers (for uniqueness validation)."""
    commands = []
    for controller in get_controllers():
        commands.extend(controller.get("bindings", {}).values())
    return commands

def get_all_bindings():
    """Get all bindings as {command: (controller_index, button_key)} for routing."""
    result = {}
    for idx, controller in enumerate(get_controllers()):
        for button, command in controller.get("bindings", {}).items():
            result[command] = (idx, button)
    return result

def find_command_controller(command):
    """Find which controller and button has a command. Returns (controller_index, button_key) or None."""
    for idx, controller in enumerate(get_controllers()):
        for button, cmd in controller.get("bindings", {}).items():
            if cmd == command:
                return (idx, button)
    return None

def add_controller():
    """Add a new controller. Returns new controller index or -1 if limit reached."""
    config = load_config()
    controllers = config.get("controllers", [])
    if len(controllers) >= 3:
        return -1
    new_index = len(controllers)
    controllers.append({
        "name": f"Controller {new_index + 1}",
        "bindings": {}
    })
    config["controllers"] = controllers
    save_config(config)
    return new_index

def remove_controller(controller_index):
    """Remove a controller by index. Returns True if successful."""
    config = load_config()
    controllers = config.get("controllers", [])
    if len(controllers) <= 1 or controller_index < 0 or controller_index >= len(controllers):
        return False
    controllers.pop(controller_index)
    config["controllers"] = controllers
    save_config(config)
    return True

def rename_binding(controller_index, button_key, new_command):
    """Rename a command for a button on a specific controller."""
    config = load_config()
    controllers = config.get("controllers", [])
    if 0 <= controller_index < len(controllers):
        controllers[controller_index]["bindings"][button_key] = new_command
        config["controllers"] = controllers
        save_config(config)
        return True
    return False

def remove_binding(controller_index, button_key):
    """Remove a binding from a controller."""
    config = load_config()
    controllers = config.get("controllers", [])
    if 0 <= controller_index < len(controllers):
        bindings = controllers[controller_index].get("bindings", {})
        if button_key in bindings:
            del bindings[button_key]
            controllers[controller_index]["bindings"] = bindings
            config["controllers"] = controllers
            save_config(config)
            return True
    return False

def get_available_buttons():
    """Get list of available gamepad buttons."""
    return load_config().get("available_buttons", [])

def get_theme():
    config = load_config()
    return config.get("theme", DEFAULT_THEME)

def get_api_key():
    key = get_setting("openai_api_key", "")
    if key:
        return key
    return os.environ.get("OPENAI_API_KEY", "")

def save_api_key(api_key):
    global _client
    _client = None  # Invalidate cached client so new key takes effect
    set_setting("openai_api_key", api_key)

def get_openai_client():
    global _client
    api_key = get_api_key()
    if not api_key:
        raise ValueError("OpenAI API key not configured. Set it in the GUI or as OPENAI_API_KEY environment variable.")
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client
