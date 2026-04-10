import vgamepad as vg
import time
from src.config_manager import get_controllers, find_command_controller

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

# Multiple gamepad instances (one per controller)
_gamepads = {}

def get_gamepad(controller_index=0):
    """Get or create a gamepad instance for a specific controller index."""
    global _gamepads
    if controller_index not in _gamepads:
        print(f"Initializing virtual controller {controller_index + 1}...")
        try:
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
    """Initialize all gamepads based on config."""
    controllers = get_controllers()
    try:
        for i in range(len(controllers)):
            get_gamepad(i)
        print(f"Initialized {len(controllers)} virtual controller(s).")
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
    """Trigger gamepad button for a command on the correct controller."""
    result = find_command_controller(command_name)
    if not result:
        return

    controller_index, button_key = result
    if button_key not in BUTTON_MAP:
        return

    button_id = BUTTON_MAP[button_key]
    pad = get_gamepad(controller_index)

    pad.press_button(button=button_id)
    pad.update()
    time.sleep(0.1)
    pad.release_button(button=button_id)
    pad.update()

def trigger_button(controller_index, button_key):
    """Directly trigger a button on a specific controller (for manual testing)."""
    if button_key not in BUTTON_MAP:
        return

    button_id = BUTTON_MAP[button_key]
    pad = get_gamepad(controller_index)

    pad.press_button(button=button_id)
    pad.update()
    time.sleep(0.1)
    pad.release_button(button=button_id)
    pad.update()