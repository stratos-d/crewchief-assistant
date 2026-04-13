import os
import json
import shutil
from datetime import datetime
from src.constants import MAX_BUTTONS

# vJoy button schema: 64 buttons, 0-indexed buttonIndex, no POV data
BUTTON_SCHEMA_VJOY = [
    {"id": str(i), "buttonIndex": i - 1, "usePovData": False, "povValue": 0}
    for i in range(1, MAX_BUTTONS + 1)
]

VJOY_DEVICE_NAME = "vJoy Device"


def action_to_command(action):
    """Convert CrewChief action name to a readable voice command."""
    # Replace underscores with spaces, lowercase
    cmd = action.replace("_", " ").lower().strip()
    # Clean up common patterns
    cmd = cmd.replace("\u2019", "'")
    return cmd


def find_vjoy_guid(devices):
    """Find the GUID of the first vJoy device in CrewChief's device list."""
    for device in devices:
        if VJOY_DEVICE_NAME in device.get("deviceName", ""):
            return device["guid"]
    return None


def get_available_actions(button_assignments):
    """Filter button assignments to only those with availableAction: true."""
    return [ba for ba in button_assignments if ba.get("availableAction", False)]


def sync_crewchief_config(crewchief_config_path, existing_controllers):
    """
    Read CrewChief's config, map available actions to the vJoy device buttons,
    and return the updated config + app bindings.
    
    Args:
        crewchief_config_path: Path to CrewChief's defaultSettings.json
        existing_controllers: List of controller dicts from the app's config
    
    Returns:
        dict with keys:
            - "success": bool
            - "message": str
            - "bindings": list of controller dicts (for app config)
            - "action_count": int
            - "truncated": bool
    """
    # Validate path
    if not os.path.exists(crewchief_config_path):
        return {
            "success": False,
            "message": f"File not found: {crewchief_config_path}",
            "bindings": [],
            "action_count": 0,
            "truncated": False,
        }

    # Read CrewChief config
    with open(crewchief_config_path, "r", encoding="utf-8") as f:
        cc_config = json.load(f)

    devices = cc_config.get("devices", [])
    button_assignments = cc_config.get("buttonAssignments", [])

    # Find vJoy device GUID
    vjoy_guid = find_vjoy_guid(devices)
    if not vjoy_guid:
        return {
            "success": False,
            "message": "No vJoy device found in CrewChief config. "
                       "Make sure vJoy is installed and CrewChief has detected it.",
            "bindings": [],
            "action_count": 0,
            "truncated": False,
        }

    if not existing_controllers:
        return {
            "success": False,
            "message": "No controller configured in the app.",
            "bindings": [],
            "action_count": 0,
            "truncated": False,
        }

    # Get available actions
    available = get_available_actions(button_assignments)
    total_slots = len(BUTTON_SCHEMA_VJOY)
    truncated = len(available) > total_slots
    actions_to_assign = available[:total_slots]

    # Backup original file
    backup_path = crewchief_config_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(crewchief_config_path, backup_path)

    app_controller = dict(existing_controllers[0])
    existing_bindings = app_controller.get("bindings", {})

    for idx, assignment in enumerate(actions_to_assign):
        btn = BUTTON_SCHEMA_VJOY[idx]

        # Update CrewChief assignment
        assignment["deviceGuid"] = vjoy_guid
        assignment["buttonIndex"] = btn["buttonIndex"]
        assignment["usePovData"] = btn["usePovData"]
        assignment["povValue"] = btn["povValue"]

        # Update app binding
        command_name = action_to_command(assignment["action"])
        existing_bindings[btn["id"]] = {"command": command_name, "enabled": True}

    # Ensure unsynced buttons retain proper format
    for key in list(existing_bindings.keys()):
        val = existing_bindings[key]
        if isinstance(val, str):
            existing_bindings[key] = {"command": val, "enabled": bool(val)}

    app_controller["bindings"] = existing_bindings

    # Clear assignments for actions beyond capacity
    for assignment in available[total_slots:]:
        assignment["deviceGuid"] = ""
        assignment["buttonIndex"] = -1
        assignment["usePovData"] = False
        assignment["povValue"] = 0

    # Write updated CrewChief config
    with open(crewchief_config_path, "w", encoding="utf-8") as f:
        json.dump(cc_config, f, indent=2)

    return {
        "success": True,
        "message": f"Synced {len(actions_to_assign)} actions to vJoy device. "
                   f"Backup saved to: {os.path.basename(backup_path)}"
                   + (f"\nWarning: {len(available) - total_slots} actions were truncated (max {total_slots})."
                      if truncated else ""),
        "bindings": [app_controller],
        "action_count": len(actions_to_assign),
        "truncated": truncated,
    }
