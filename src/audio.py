import sounddevice as sd
import keyboard
import numpy as np
import scipy.io.wavfile as wav
import io
import time
from src.config_manager import get_setting
from src.sounds import play_ptt_on, play_ptt_off


def get_input_devices():
    """Get list of available audio input devices."""
    devices = sd.query_devices()
    input_devices = []
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            input_devices.append({
                'id': i,
                'name': dev['name'],
                'channels': dev['max_input_channels']
            })
    return input_devices


def get_device_id():
    """Get the configured input device ID, or None for default."""
    device_name = get_setting("audio.input_device", "")
    if not device_name:
        return None

    # Find device by name
    for dev in get_input_devices():
        if dev['name'] == device_name:
            return dev['id']
    return None


def record_command(ptt_key, stop_event=None, on_start=None, on_stop=None):
    """Records audio while PTT is held. Can be interrupted by stop_event."""

    SAMPLE_RATE = get_setting("audio.sample_rate", 44100)
    device_id = get_device_id()

    # Wait for the user to press the key, or for the GUI to send a stop signal
    while True:
        if stop_event and stop_event.is_set():
            return None
        if keyboard.is_pressed(ptt_key):
            break
        time.sleep(0.05)  # Tiny sleep to prevent maxing out the CPU

    # Play PTT on sound and notify GUI
    play_ptt_on()
    if on_start: on_start()

    audio_chunks = []

    def callback(indata, frames, time_info, status):
        audio_chunks.append(indata.copy())

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, device=device_id, callback=callback):
        # Keep recording until they let go OR click the stop button
        while keyboard.is_pressed(ptt_key):
            if stop_event and stop_event.is_set():
                break
            sd.sleep(50)

    # Play PTT off sound and notify GUI
    play_ptt_off()
    if on_stop: on_stop()

    if len(audio_chunks) > 0:
        recording = np.concatenate(audio_chunks, axis=0)
        virtual_file = io.BytesIO()
        wav.write(virtual_file, SAMPLE_RATE, recording)
        virtual_file.name = "audio.wav"
        virtual_file.seek(0)
        return virtual_file
    else:
        return None