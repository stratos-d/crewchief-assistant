import os
import json
import shutil
from datetime import datetime

# Hardware schema: button order for sequential assignment
BUTTON_SCHEMA = [
    {"id": "A", "buttonIndex": 0, "usePovData": False, "povValue": 0},
    {"id": "B", "buttonIndex": 1, "usePovData": False, "povValue": 0},
    {"id": "X", "buttonIndex": 2, "usePovData": False, "povValue": 0},
    {"id": "Y", "buttonIndex": 3, "usePovData": False, "povValue": 0},
    {"id": "LEFT_SHOULDER", "buttonIndex": 4, "usePovData": False, "povValue": 0},
    {"id": "RIGHT_SHOULDER", "buttonIndex": 5, "usePovData": False, "povValue": 0},
    {"id": "BACK", "buttonIndex": 6, "usePovData": False, "povValue": 0},
    {"id": "START", "buttonIndex": 7, "usePovData": False, "povValue": 0},
    {"id": "LEFT_THUMB", "buttonIndex": 8, "usePovData": False, "povValue": 0},
    {"id": "RIGHT_THUMB", "buttonIndex": 9, "usePovData": False, "povValue": 0},
    {"id": "DPAD_UP", "buttonIndex": 0, "usePovData": True, "povValue": 0},
    {"id": "DPAD_RIGHT", "buttonIndex": 0, "usePovData": True, "povValue": 9000},
    {"id": "DPAD_DOWN", "buttonIndex": 0, "usePovData": True, "povValue": 18000},
    {"id": "DPAD_LEFT", "buttonIndex": 0, "usePovData": True, "povValue": 27000},
]

BUTTONS_PER_CONTROLLER = len(BUTTON_SCHEMA)
MAX_CONTROLLERS = 3
MAX_ACTIONS = BUTTONS_PER_CONTROLLER * MAX_CONTROLLERS


def action_to_command(action):
    """Convert CrewChief action name to a readable voice command."""
    # Replace underscores with spaces, lowercase
    cmd = action.replace("_", " ").lower().strip()
    # Clean up common patterns
    cmd = cmd.replace("'", "'")
    return cmd


def extract_xbox_guids(devices):
    """Extract GUIDs for virtual Xbox 360 controllers from the devices list."""
    guids = []
    for device in devices:
        if "XBOX 360 For Windows" in device.get("deviceName", ""):
            guids.append(device["guid"])
    return guids


def get_available_actions(button_assignments):
    """Filter button assignments to only those with availableAction: true."""
    return [ba for ba in button_assignments if ba.get("availableAction", False)]


def sync_crewchief_config(crewchief_config_path, existing_controllers):
    """
    Read CrewChief's config, map available actions to existing virtual controller buttons,
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

    # Extract virtual controller GUIDs
    guids = extract_xbox_guids(devices)
    if not guids:
        return {
            "success": False,
            "message": "No virtual Xbox 360 controllers found in CrewChief config. "
                       "Make sure the app is running and CrewChief has discovered the controllers.",
            "bindings": [],
            "action_count": 0,
            "truncated": False,
        }

    # Only sync with existing controllers from the app
    if not existing_controllers:
        return {
            "success": False,
            "message": "No controllers found in the app. Add controllers first using ADD CONTROLLER.",
            "bindings": [],
            "action_count": 0,
            "truncated": False,
        }

    # Limit GUIDs to match existing controller count
    max_controllers = min(len(existing_controllers), MAX_CONTROLLERS)
    guids = guids[:max_controllers]

    if len(guids) < len(existing_controllers):
        return {
            "success": False,
            "message": f"Not enough virtual controllers found in CrewChief config. Found {len(guids)}, but app has {len(existing_controllers)}. Make sure CrewChief has discovered all controllers.",
            "bindings": [],
            "action_count": 0,
            "truncated": False,
        }

    # Get available actions
    available = get_available_actions(button_assignments)
    truncated = len(available) > len(guids) * BUTTONS_PER_CONTROLLER
    max_assignable = len(guids) * BUTTONS_PER_CONTROLLER
    actions_to_assign = available[:max_assignable]

    # Backup original file
    backup_path = crewchief_config_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(crewchief_config_path, backup_path)

    # Use existing controller structure from app
    app_controllers = []
    for controller in existing_controllers[:max_controllers]:
        app_controllers.append({
            "name": controller.get("name", f"Controller {len(app_controllers) + 1}"),
            "bindings": controller.get("bindings", {})
        })

    for idx, assignment in enumerate(actions_to_assign):
        controller_idx = idx // BUTTONS_PER_CONTROLLER
        button_idx = idx % BUTTONS_PER_CONTROLLER
        schema = BUTTON_SCHEMA[button_idx]
        guid = guids[controller_idx]

        # Update CrewChief assignment
        assignment["deviceGuid"] = guid
        assignment["buttonIndex"] = schema["buttonIndex"]
        assignment["usePovData"] = schema["usePovData"]
        assignment["povValue"] = schema["povValue"]

        # Only update app binding if this button already exists in the controller
        existing_bindings = app_controllers[controller_idx]["bindings"]
        if schema["id"] in existing_bindings:
            command_name = action_to_command(assignment["action"])
            existing_bindings[schema["id"]] = command_name

    # Clear assignments for actions beyond capacity (if any were previously assigned)
    for assignment in available[max_assignable:]:
        assignment["deviceGuid"] = ""
        assignment["buttonIndex"] = -1
        assignment["usePovData"] = False
        assignment["povValue"] = 0

    # Write updated CrewChief config
    with open(crewchief_config_path, "w", encoding="utf-8") as f:
        json.dump(cc_config, f, indent=2)

    return {
        "success": True,
        "message": f"Synced {len(actions_to_assign)} actions across {len(guids)} controller(s). "
                   f"Backup saved to: {os.path.basename(backup_path)}"
                   + (f"\nWarning: {len(available) - max_assignable} actions were truncated (max {max_assignable})."
                      if truncated else ""),
        "bindings": app_controllers,
        "action_count": len(actions_to_assign),
        "truncated": truncated,
    }
