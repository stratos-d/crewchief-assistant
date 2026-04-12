import vgamepad as vg
import time
from src.config_manager import get_controllers, find_command_controller
from src.constants import ControllerType

BUTTON_MAP = {
    # Face buttons
    "A": vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "B": vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "X": vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "Y": vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    # D-Pad
    "DPAD_UP": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    "DPAD_DOWN": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    "DPAD_LEFT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    "DPAD_RIGHT": vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    # Shoulders (bumpers)
    "LEFT_SHOULDER": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "RIGHT_SHOULDER": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    # Thumb sticks (click)
    "LEFT_THUMB": vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    "RIGHT_THUMB": vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    # Menu buttons
    "BACK": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    "START": vg.XUSB_BUTTON.XUSB_GAMEPAD_START
}

DS4_BUTTON_MAP = {
    "CROSS":    vg.DS4_BUTTONS.DS4_BUTTON_CROSS,
    "CIRCLE":   vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE,
    "SQUARE":   vg.DS4_BUTTONS.DS4_BUTTON_SQUARE,
    "TRIANGLE": vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE,
    "L1":       vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT,
    "R1":       vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT,
    "L3":       vg.DS4_BUTTONS.DS4_BUTTON_THUMB_LEFT,
    "R3":       vg.DS4_BUTTONS.DS4_BUTTON_THUMB_RIGHT,
    "OPTIONS":  vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS,
    "SHARE":    vg.DS4_BUTTONS.DS4_BUTTON_SHARE,
}

DS4_DPAD_MAP = {
    "DPAD_UP":    vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH,
    "DPAD_DOWN":  vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH,
    "DPAD_LEFT":  vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST,
    "DPAD_RIGHT": vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST,
}

# Multiple gamepad instances (one per controller)
_gamepads = {}

def _get_ctrl_type(controller_index):
    """Resolve ControllerType for a given index."""
    controllers = get_controllers()
    raw = controllers[controller_index].get("type", ControllerType.X360) if controller_index < len(controllers) else ControllerType.X360
    return ControllerType(raw)

def get_gamepad(controller_index=0):
    """Get or create a gamepad instance for a specific controller index."""
    global _gamepads
    if controller_index not in _gamepads:
        ctrl_type = _get_ctrl_type(controller_index)
        print(f"Initializing virtual controller {controller_index + 1} ({ctrl_type.label})...")
        try:
            if ctrl_type == ControllerType.DS4:
                _gamepads[controller_index] = vg.VDS4Gamepad()
            else:
                _gamepads[controller_index] = vg.VX360Gamepad()
        except Exception as e:
            raise RuntimeError(
                "Failed to create virtual controller. "
                "Make sure ViGEmBus is installed: "
                "https://github.com/nefarius/ViGEmBus/releases"
            ) from e
        time.sleep(0.5)
    return _gamepads[controller_index]

def init_all_gamepads():
    """Initialize virtual gamepads for gamepad-type controllers only."""
    controllers = get_controllers()
    gamepad_indices = [
        i for i, c in enumerate(controllers)
        if ControllerType(c.get("type", ControllerType.X360)).is_virtual
    ]
    if not gamepad_indices:
        print("No virtual gamepad controllers configured.")
        return
    try:
        for i in gamepad_indices:
            get_gamepad(i)
        print(f"Initialized {len(gamepad_indices)} virtual controller(s).")
    except RuntimeError as e:
        print(f"ERROR: {e}")

def release_gamepad(controller_index):
    """Release and remove a virtual gamepad."""
    global _gamepads
    if controller_index in _gamepads:
        try:
            # Reset all inputs before releasing
            pad = _gamepads[controller_index]
            pad.reset()
            pad.update()
            # Delete the gamepad (triggers cleanup)
            del _gamepads[controller_index]
            print(f"Released virtual controller {controller_index + 1}")
        except Exception as e:
            print(f"Error releasing controller: {e}")

    # Re-index remaining gamepads if needed
    # When controller at index N is removed, controllers N+1, N+2... need to shift
    new_gamepads = {}
    for old_idx in sorted(_gamepads.keys()):
        if old_idx > controller_index:
            new_gamepads[old_idx - 1] = _gamepads[old_idx]
        else:
            new_gamepads[old_idx] = _gamepads[old_idx]
    _gamepads = new_gamepads

def trigger_action(command_name):
    """Trigger button for a command on a virtual gamepad controller."""
    result = find_command_controller(command_name)
    if not result:
        return

    controller_index, button_key = result
    ctrl_type = _get_ctrl_type(controller_index)
    _press_gamepad_button(controller_index, ctrl_type, button_key)

def trigger_button(controller_index, button_key):
    """Directly trigger a button on a specific controller (for manual testing)."""
    ctrl_type = _get_ctrl_type(controller_index)
    _press_gamepad_button(controller_index, ctrl_type, button_key)

def _press_gamepad_button(controller_index, ctrl_type, button_key):
    """Internal: press and release a button on an x360 or ds4 virtual gamepad."""
    pad = get_gamepad(controller_index)

    if ctrl_type == ControllerType.DS4:
        if button_key in DS4_DPAD_MAP:
            pad.directional_pad(direction=DS4_DPAD_MAP[button_key])
            pad.update()
            time.sleep(0.1)
            pad.directional_pad(direction=vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE)
            pad.update()
        elif button_key in DS4_BUTTON_MAP:
            pad.press_button(button=DS4_BUTTON_MAP[button_key])
            pad.update()
            time.sleep(0.1)
            pad.release_button(button=DS4_BUTTON_MAP[button_key])
            pad.update()
    else:
        if button_key not in BUTTON_MAP:
            return
        button_id = BUTTON_MAP[button_key]
        pad.press_button(button=button_id)
        pad.update()
        time.sleep(0.1)
        pad.release_button(button=button_id)
        pad.update()