import os
import sys
import threading
from src.config_manager import get_setting

# Path to resources folder (supports PyInstaller bundled mode)
if getattr(sys, 'frozen', False):
    _BASE = sys._MEIPASS
else:
    _BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESOURCES_DIR = os.path.join(_BASE, "resources")
PTT_ON_SOUND = os.path.join(RESOURCES_DIR, "PTT_ON.mp3")
PTT_OFF_SOUND = os.path.join(RESOURCES_DIR, "PTT_OFF.mp3")

_pygame = None
_sounds = {}


def _init_pygame():
    """Initialize pygame mixer for audio playback."""
    global _pygame
    if _pygame is not None:
        return True

    try:
        import pygame
        pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
        _pygame = pygame

        # Pre-load sounds as WAV-compatible Sound objects won't work with MP3
        # Use mixer.music for MP3 or convert to WAV
        return True
    except Exception as e:
        print(f"Sound init failed: {e}")
        return False


def _play_sound(filepath):
    """Play a sound file."""
    if not _init_pygame():
        return

    try:
        # Use a separate channel for each sound to allow overlapping
        if filepath not in _sounds:
            _sounds[filepath] = _pygame.mixer.Sound(filepath)

        _sounds[filepath].play()
    except Exception as e:
        # MP3 might not work with Sound(), try music instead
        try:
            _pygame.mixer.music.load(filepath)
            _pygame.mixer.music.play()
        except Exception as e2:
            print(f"Sound playback failed: {e2}")


def play_ptt_on():
    """Play PTT on sound if enabled."""
    if get_setting("audio.ptt_sound_enabled", True):
        threading.Thread(target=lambda: _play_sound(PTT_ON_SOUND), daemon=True).start()


def play_ptt_off():
    """Play PTT off sound if enabled."""
    if get_setting("audio.ptt_sound_enabled", True):
        threading.Thread(target=lambda: _play_sound(PTT_OFF_SOUND), daemon=True).start()
