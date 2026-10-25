import os
import sys
import winsound
from src.config_manager import get_setting

# Path to resources folder (supports PyInstaller bundled mode)
if getattr(sys, 'frozen', False):
    _BASE = sys._MEIPASS
else:
    _BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_DIR = os.path.join(_BASE, "resources")
PTT_ON_SOUND = os.path.join(RESOURCES_DIR, "PTT_ON.wav")
PTT_OFF_SOUND = os.path.join(RESOURCES_DIR, "PTT_OFF.wav")
NOT_UNDERSTOOD_SOUND = os.path.join(RESOURCES_DIR, "NOT_UNDERSTOOD.wav")


def _play_sound(filepath):
    """Play a WAV file without blocking (the built-in Windows player needs no setup)."""
    try:
        winsound.PlaySound(filepath, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
    except RuntimeError as e:
        print(f"Sound playback failed: {e}")


def play_ptt_on():
    """Play PTT on sound if enabled."""
    if get_setting("audio.ptt_sound_enabled", True):
        _play_sound(PTT_ON_SOUND)


def play_ptt_off():
    """Play PTT off sound if enabled."""
    if get_setting("audio.ptt_sound_enabled", True):
        _play_sound(PTT_OFF_SOUND)


def play_not_understood():
    """Tell the driver, without looking, that no button was pressed and they should try again."""
    if get_setting("audio.ptt_sound_enabled", True):
        _play_sound(NOT_UNDERSTOOD_SOUND)
