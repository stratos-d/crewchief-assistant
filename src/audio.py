import sounddevice as sd
import keyboard
import collections
import threading
import wave
import io
import time
from src.config_manager import get_setting
from src.sounds import play_ptt_on, play_ptt_off

# Whisper works at 16 kHz, so recording 16-bit 16 kHz keeps uploads ~5x smaller than 44.1 kHz float
SAMPLE_RATE = 16000
BLOCK_FRAMES = SAMPLE_RATE // 50  # 20 ms per callback
PRE_ROLL_BLOCKS = 15  # Keep 300 ms from before the PTT press, so the first word isn't clipped
POLL_SECONDS = 0.01


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


class Microphone:
    """Input stream that stays open while the assistant runs, so recording starts instantly on PTT."""

    def __init__(self):
        self._lock = threading.Lock()
        self._pre_roll = collections.deque(maxlen=PRE_ROLL_BLOCKS)
        self._recording = None
        self._stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=BLOCK_FRAMES,
            latency="low", device=get_device_id(), callback=self._on_audio
        )
        self._stream.start()

    def _on_audio(self, indata, frames, time_info, status):
        with self._lock:
            target = self._recording if self._recording is not None else self._pre_roll
            target.append(bytes(indata))

    def start_recording(self):
        with self._lock:
            self._recording = list(self._pre_roll)
            self._pre_roll.clear()

    def stop_recording(self):
        """Stop recording and return the captured 16-bit PCM bytes."""
        # Wait until audio captured right up to the release has been delivered
        time.sleep(self._stream.latency + BLOCK_FRAMES / SAMPLE_RATE)
        with self._lock:
            chunks, self._recording = self._recording, None
        return b"".join(chunks or [])

    def close(self):
        self._stream.close()


def encode_wav(pcm):
    """Wrap 16-bit mono PCM in an in-memory WAV file for the OpenAI upload."""
    virtual_file = io.BytesIO()
    with wave.open(virtual_file, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm)
    virtual_file.name = "audio.wav"
    virtual_file.seek(0)
    return virtual_file


def record_command(mic, ptt_key, stop_event=None, on_start=None, on_stop=None):
    """Records audio while PTT is held. Can be interrupted by stop_event."""

    # Wait for the user to press the key, or for the GUI to send a stop signal
    while True:
        if stop_event and stop_event.is_set():
            return None
        if keyboard.is_pressed(ptt_key):
            break
        time.sleep(POLL_SECONDS)

    mic.start_recording()

    # Play PTT on sound and notify GUI
    play_ptt_on()
    if on_start: on_start()

    # Keep recording until they let go OR click the stop button
    while keyboard.is_pressed(ptt_key):
        if stop_event and stop_event.is_set():
            break
        time.sleep(POLL_SECONDS)

    pcm = mic.stop_recording()

    # Play PTT off sound and notify GUI
    play_ptt_off()
    if on_stop: on_stop()

    return encode_wav(pcm) if pcm else None
