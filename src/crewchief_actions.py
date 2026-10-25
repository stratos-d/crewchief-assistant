"""What CrewChief has on each vJoy button, named the way CrewChief's own controller list names it."""
import json
import os

from src.crewchief_sync import find_vjoy_guid

INSTALL_DIRS = [
    os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Britton IT Ltd", "CrewChiefV4"),
    os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Britton IT Ltd", "CrewChiefV4"),
]

_labels_cache = {}


def _read_pairs(path, first_phrase=False):
    """'KEY = value' lines from one of CrewChief's text files.

    Voice actions list several phrases separated by ':'; CrewChief shows the first one.
    """
    pairs = {}
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as f:
            for line in f:
                if line.lstrip().startswith("#"):
                    continue
                key, sep, value = line.partition("=")
                if not sep:
                    continue
                value = value.strip()
                if first_phrase:
                    value = value.split(":")[0].strip()
                pairs[key.strip()] = value.replace("&", "")  # '&' marks a Windows menu shortcut
    except OSError:
        pass
    return pairs


def load_labels(install_dir=None):
    """Action id -> CrewChief's name for it, from the CrewChief install. Empty if CrewChief isn't found."""
    if install_dir is None:
        install_dir = next((d for d in INSTALL_DIRS if os.path.isdir(d)), None)
    if not install_dir:
        return {}
    files = [os.path.join(install_dir, "ui_text", "en.txt"), os.path.join(install_dir, "speech_recognition_config.txt")]
    stamp = tuple(os.path.getmtime(p) if os.path.exists(p) else 0 for p in files)
    cached = _labels_cache.get(install_dir)
    if cached and cached[0] == stamp:
        return cached[1]
    labels = _read_pairs(files[0])
    labels.update(_read_pairs(files[1], first_phrase=True))
    _labels_cache[install_dir] = (stamp, labels)
    return labels


def action_label(action, labels):
    """CrewChief's name for an action, e.g. DO_I_HAVE_A_PENALTY -> 'Do I have a penalty'."""
    text = labels.get(action) or labels.get(action.lower()) or action.replace("_", " ").lower()
    return text[:1].upper() + text[1:]


def vjoy_actions(crewchief_config_path, install_dir=None):
    """{vJoy button number: CrewChief action name} for every action CrewChief has on the vJoy device.

    Returns None when CrewChief's settings can't be read, so callers can tell "nothing bound" from "unknown".
    """
    try:
        with open(crewchief_config_path, "r", encoding="utf-8") as f:
            cc_config = json.load(f)
        assignments = cc_config.get("buttonAssignments", [])
        guid = find_vjoy_guid(cc_config.get("devices", []))
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    if not guid:
        return {}

    labels = load_labels(install_dir)
    actions = {}
    for assignment in assignments:
        index = assignment.get("buttonIndex", -1)
        if assignment.get("deviceGuid") != guid or not isinstance(index, int) or index < 0 or assignment.get("usePovData"):
            continue
        label = action_label(assignment.get("action", ""), labels)
        button = index + 1  # CrewChief counts buttons from 0, vJoy from 1
        actions[button] = f"{actions[button]} / {label}" if button in actions else label
    return actions
