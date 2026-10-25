import pyvjoy
import time
from src.config_manager import find_command_controller
from src.constants import VJOY_DEVICE_ID, MAX_BUTTONS

_device = None


def _get_device():
    """Get or create the vJoy device instance."""
    global _device
    if _device is None:
        try:
            _device = pyvjoy.VJoyDevice(VJOY_DEVICE_ID)
        except Exception as e:
            raise RuntimeError(
                "Failed to acquire vJoy device. "
                "Make sure vJoy is installed and device 1 is enabled: "
                "https://sourceforge.net/projects/vjoystick/"
            ) from e
    return _device


def _button_count():
    """Buttons enabled on the vJoy device (vJoy defaults to 8; the app can use up to 64)."""
    try:
        return int(pyvjoy._sdk._vj.GetVJDButtonNumber(VJOY_DEVICE_ID))
    except Exception:
        return None


def init_vjoy():
    """Initialize the vJoy device. Returns {"ok": bool, "buttons": int or None} for the setup checklist."""
    try:
        dev = _get_device()
        dev.reset()
        buttons = _button_count()
        print(f"vJoy device {VJOY_DEVICE_ID} initialized ({buttons or MAX_BUTTONS} buttons).")
        return {"ok": True, "buttons": buttons}
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return {"ok": False, "buttons": None}


def release_vjoy():
    """Release the vJoy device."""
    global _device
    if _device is not None:
        try:
            _device.reset()
            _device = None
            print(f"Released vJoy device {VJOY_DEVICE_ID}")
        except Exception as e:
            print(f"Error releasing vJoy device: {e}")


def trigger_action(command_name):
    """Trigger button for a command via the vJoy device. Returns the button number pressed, or None."""
    result = find_command_controller(command_name)
    if not result:
        print(f"No enabled button is bound to '{command_name}'.")
        return None

    _controller_index, button_key = result
    _press_button(int(button_key))
    return int(button_key)


def trigger_button(controller_index, button_key):
    """Directly trigger a button (for manual testing). controller_index is ignored (single device)."""
    _press_button(int(button_key))


def _press_button(button_id):
    """Press and release a single vJoy button (1-based)."""
    if button_id < 1 or button_id > MAX_BUTTONS:
        return
    dev = _get_device()
    dev.set_button(button_id, 1)
    time.sleep(0.1)
    dev.set_button(button_id, 0)