import os
import json
import shutil
from datetime import datetime
from src.constants import ControllerType

# Hardware schema: button order for sequential assignment (X360)
BUTTON_SCHEMA_X360 = [
    {"id": "A",              "buttonIndex": 0, "usePovData": False, "povValue": 0},
    {"id": "B",              "buttonIndex": 1, "usePovData": False, "povValue": 0},
    {"id": "X",              "buttonIndex": 2, "usePovData": False, "povValue": 0},
    {"id": "Y",              "buttonIndex": 3, "usePovData": False, "povValue": 0},
    {"id": "LEFT_SHOULDER",  "buttonIndex": 4, "usePovData": False, "povValue": 0},
    {"id": "RIGHT_SHOULDER", "buttonIndex": 5, "usePovData": False, "povValue": 0},
    {"id": "BACK",           "buttonIndex": 6, "usePovData": False, "povValue": 0},
    {"id": "START",          "buttonIndex": 7, "usePovData": False, "povValue": 0},
    {"id": "LEFT_THUMB",     "buttonIndex": 8, "usePovData": False, "povValue": 0},
    {"id": "RIGHT_THUMB",    "buttonIndex": 9, "usePovData": False, "povValue": 0},
    {"id": "DPAD_UP",        "buttonIndex": 0, "usePovData": True,  "povValue": 0},
    {"id": "DPAD_RIGHT",     "buttonIndex": 0, "usePovData": True,  "povValue": 9000},
    {"id": "DPAD_DOWN",      "buttonIndex": 0, "usePovData": True,  "povValue": 18000},
    {"id": "DPAD_LEFT",      "buttonIndex": 0, "usePovData": True,  "povValue": 27000},
]

# DS4 button schema — DirectInput indices (L2=6, R2=7 occupy slots between R1 and SHARE)
BUTTON_SCHEMA_DS4 = [
    {"id": "CROSS",    "buttonIndex": 1,  "usePovData": False, "povValue": 0},
    {"id": "CIRCLE",   "buttonIndex": 2,  "usePovData": False, "povValue": 0},
    {"id": "SQUARE",   "buttonIndex": 0,  "usePovData": False, "povValue": 0},
    {"id": "TRIANGLE", "buttonIndex": 3,  "usePovData": False, "povValue": 0},
    {"id": "L1",       "buttonIndex": 4,  "usePovData": False, "povValue": 0},
    {"id": "R1",       "buttonIndex": 5,  "usePovData": False, "povValue": 0},
    {"id": "SHARE",    "buttonIndex": 8,  "usePovData": False, "povValue": 0},
    {"id": "OPTIONS",  "buttonIndex": 9,  "usePovData": False, "povValue": 0},
    {"id": "L3",       "buttonIndex": 10, "usePovData": False, "povValue": 0},
    {"id": "R3",       "buttonIndex": 11, "usePovData": False, "povValue": 0},
    {"id": "DPAD_UP",  "buttonIndex": 0,  "usePovData": True,  "povValue": 0},
    {"id": "DPAD_RIGHT","buttonIndex": 0, "usePovData": True,  "povValue": 9000},
    {"id": "DPAD_DOWN","buttonIndex": 0,  "usePovData": True,  "povValue": 18000},
    {"id": "DPAD_LEFT","buttonIndex": 0,  "usePovData": True,  "povValue": 27000},
]

BUTTON_SCHEMA_BY_TYPE = {
    ControllerType.X360: BUTTON_SCHEMA_X360,
    ControllerType.DS4: BUTTON_SCHEMA_DS4,
}

BUTTONS_PER_CONTROLLER = len(BUTTON_SCHEMA_X360)
MAX_CONTROLLERS = 3
MAX_ACTIONS = BUTTONS_PER_CONTROLLER * MAX_CONTROLLERS


def action_to_command(action):
    """Convert CrewChief action name to a readable voice command."""
    # Replace underscores with spaces, lowercase
    cmd = action.replace("_", " ").lower().strip()
    # Clean up common patterns
    cmd = cmd.replace("'", "'")
    return cmd


# Device identification: (name_substring, deviceType) — either match is sufficient
DEVICE_PATTERNS = {
    ControllerType.X360:     ("XBOX 360 For Windows", None),
    ControllerType.DS4:      ("Wireless Controller",  24),
}


def extract_guids_by_type(devices):
    """Return a dict mapping ControllerType -> list of GUIDs found in CrewChief devices."""
    result = {t: [] for t in DEVICE_PATTERNS}
    for device in devices:
        name = device.get("deviceName", "")
        dtype = device.get("deviceType")
        for ctrl_type, (name_pattern, type_id) in DEVICE_PATTERNS.items():
            if name_pattern in name or (type_id is not None and dtype == type_id):
                result[ctrl_type].append(device["guid"])
                break
    # Sort by ViGEm serial embedded in GUID (4th segment, e.g. "8001")
    # to match the app's sequential controller creation order.
    for t in result:
        result[t].sort(key=lambda g: g.split("-")[3])
    return result


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

    # Extract virtual controller GUIDs grouped by type
    guids_by_type = extract_guids_by_type(devices)
    # Build a flat ordered list of GUIDs matching the gamepad controllers in the app
    # (resolved below after gamepad_controllers is determined)

    # Collect all syncable controllers (virtual gamepads only)
    syncable_controllers = [c for c in existing_controllers if c.get("type") in BUTTON_SCHEMA_BY_TYPE]
    if not syncable_controllers:
        return {
            "success": False,
            "message": "No controllers found to sync.",
            "bindings": [],
            "action_count": 0,
            "truncated": False,
        }

    # Build ordered GUID list matching each controller by type
    type_counters = {t: 0 for t in DEVICE_PATTERNS}
    guids = []
    missing = []
    for ctrl in syncable_controllers:
        ctrl_type = ControllerType(ctrl.get("type", ControllerType.X360))
        idx = type_counters[ctrl_type]
        available = guids_by_type.get(ctrl_type, [])
        if idx < len(available):
            guids.append(available[idx])
        else:
            missing.append(ctrl_type.label)
        type_counters[ctrl_type] += 1

    if missing:
        return {
            "success": False,
            "message": f"Missing controllers in CrewChief config: {', '.join(missing)}. "
                       "Make sure the app is running and CrewChief has detected all controllers.",
            "bindings": [],
            "action_count": 0,
            "truncated": False,
        }

    max_controllers = min(len(syncable_controllers), MAX_CONTROLLERS)

    # Get available actions (each controller has its own schema length)
    available = get_available_actions(button_assignments)
    total_slots = sum(len(BUTTON_SCHEMA_BY_TYPE[ControllerType(c.get("type", ControllerType.X360))]) for c in syncable_controllers)
    truncated = len(available) > total_slots
    actions_to_assign = available[:total_slots]

    # Backup original file
    backup_path = crewchief_config_path + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(crewchief_config_path, backup_path)

    # Build index: syncable controller position -> index in app_controllers
    app_controllers = list(existing_controllers)
    syncable_indices = [i for i, c in enumerate(app_controllers) if c.get("type") in BUTTON_SCHEMA_BY_TYPE]

    # Pre-compute slot offsets per syncable controller
    slot_offsets = []  # (start_slot, schema) for each syncable controller
    offset = 0
    for ctrl in syncable_controllers:
        schema = BUTTON_SCHEMA_BY_TYPE[ControllerType(ctrl.get("type", ControllerType.X360))]
        slot_offsets.append((offset, schema))
        offset += len(schema)

    for idx, assignment in enumerate(actions_to_assign):
        # Find which syncable controller this slot belongs to
        sync_ctrl_idx = next(
            i for i, (start, schema) in enumerate(slot_offsets)
            if start <= idx < start + len(schema)
        )
        button_idx = idx - slot_offsets[sync_ctrl_idx][0]
        ctrl_schema = slot_offsets[sync_ctrl_idx][1]
        btn = ctrl_schema[button_idx]
        guid = guids[sync_ctrl_idx]
        app_ctrl_idx = syncable_indices[sync_ctrl_idx]

        # Update CrewChief assignment
        assignment["deviceGuid"] = guid
        assignment["buttonIndex"] = btn["buttonIndex"]
        assignment["usePovData"] = btn["usePovData"]
        assignment["povValue"] = btn["povValue"]

        # Only update app binding if this button already exists in the controller
        existing_bindings = app_controllers[app_ctrl_idx]["bindings"]
        if btn["id"] in existing_bindings:
            command_name = action_to_command(assignment["action"])
            existing_bindings[btn["id"]] = command_name

    # Clear assignments for actions beyond capacity (if any were previously assigned)
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
        "message": f"Synced {len(actions_to_assign)} actions across {len(guids)} controller(s). "
                   f"Backup saved to: {os.path.basename(backup_path)}"
                   + (f"\nWarning: {len(available) - total_slots} actions were truncated (max {total_slots})."
                      if truncated else ""),
        "bindings": app_controllers,
        "action_count": len(actions_to_assign),
        "truncated": truncated,
    }
