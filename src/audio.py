import sounddevice as sd
import keyboard
import array
import wave
import io
import time
from dataclasses import dataclass
from src.config_manager import get_setting
from src.sounds import play_ptt_on, play_ptt_off

# Whisper works at 16 kHz, so recording 16-bit 16 kHz keeps uploads ~5x smaller than 44.1 kHz float
SAMPLE_RATE = 16000
BLOCK_FRAMES = SAMPLE_RATE // 50  # 20 ms per callback
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
    """The input device, opened only while push-to-talk is held."""

    def __init__(self):
        self._device = get_device_id()
        # Checks the device without opening it, so a missing microphone is reported when listening starts
        sd.check_input_settings(device=self._device, channels=1, dtype="int16", samplerate=SAMPLE_RATE)
        self._chunks = []
        self._stream = None

    def _on_audio(self, indata, frames, time_info, status):
        self._chunks.append(bytes(indata))

    def start_recording(self):
        self._chunks = []
        self._stream = sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=BLOCK_FRAMES,
                                         latency="low", device=self._device, callback=self._on_audio)
        self._stream.start()

    def stop_recording(self):
        """Close the device and return the captured 16-bit PCM bytes."""
        stream, self._stream = self._stream, None
        if stream is None:
            return b""
        # Wait until audio captured right up to the release has been delivered
        time.sleep(stream.latency + BLOCK_FRAMES / SAMPLE_RATE)
        stream.stop()
        stream.close()
        return b"".join(self._chunks)

    def close(self):
        if self._stream is not None:
            self._stream.close()
            self._stream = None


@dataclass
class Clip:
    """One push-to-talk recording."""
    wav: io.BytesIO
    seconds: float


def peak_level(pcm):
    """Loudest sample in 16-bit PCM, 0..1."""
    return max(map(abs, array.array("h", pcm)), default=0) / 32768


class LevelMeter:
    """Input stream that only measures loudness, for the setup wizard's microphone check."""

    def __init__(self):
        self.level = 0.0  # peak of the latest block, 0..1
        self._stream = sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", blocksize=BLOCK_FRAMES,
                                         device=get_device_id(), callback=self._on_audio)
        self._stream.start()

    def _on_audio(self, indata, frames, time_info, status):
        self.level = peak_level(bytes(indata))

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
    """Records audio while PTT is held and returns a Clip. Can be interrupted by stop_event."""

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

    if not pcm:
        return None
    return Clip(wav=encode_wav(pcm), seconds=len(pcm) / 2 / SAMPLE_RATE)
