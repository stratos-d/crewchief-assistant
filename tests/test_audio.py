import array
import threading
import time
import wave

import pytest
import sounddevice as sd

import src.audio as audio
import src.sounds as sounds


def has_microphone():
    try:
        sd.query_devices(kind="input")
        return True
    except Exception:
        return False


needs_mic = pytest.mark.skipif(not has_microphone(), reason="no microphone (e.g. CI runner)")


def wav_seconds(buf):
    with wave.open(buf, "rb") as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, audio.SAMPLE_RATE)
        return w.getnframes() / w.getframerate()


def test_encode_wav_roundtrip():
    buf = audio.encode_wav(b"\x00\x01" * audio.SAMPLE_RATE)
    assert buf.name == "audio.wav"
    assert wav_seconds(buf) == pytest.approx(1.0)


@pytest.mark.parametrize("path", [sounds.PTT_ON_SOUND, sounds.PTT_OFF_SOUND, sounds.NOT_UNDERSTOOD_SOUND])
def test_sound_files_are_valid_wavs(path):
    with wave.open(path, "rb") as w:
        assert w.getnframes() > 0


def test_peak_level():
    assert audio.peak_level(b"") == 0
    assert audio.peak_level(array.array("h", [0, 100, -200]).tobytes()) == 200 / 32768
    assert audio.peak_level(array.array("h", [-32768]).tobytes()) == 1.0


@needs_mic
def test_microphone_is_open_only_while_recording():
    mic = audio.Microphone()
    try:
        assert mic._stream is None
        mic.start_recording()
        time.sleep(0.5)
        pcm = mic.stop_recording()
        assert mic._stream is None
    finally:
        mic.close()
    seconds = len(pcm) / 2 / audio.SAMPLE_RATE
    assert 0.4 <= seconds <= 0.7  # 0.5 s held, minus device start-up, plus delivery tail


@needs_mic
def test_record_command_follows_the_key(monkeypatch):
    monkeypatch.setattr(audio, "play_ptt_on", lambda: None)
    monkeypatch.setattr(audio, "play_ptt_off", lambda: None)
    start = time.perf_counter()
    monkeypatch.setattr(audio.keyboard, "is_pressed", lambda key: 0.3 <= time.perf_counter() - start < 1.3)
    pressed_at = {}
    mic = audio.Microphone()
    try:
        clip = audio.record_command(mic, "f8", threading.Event(),
                                    on_start=lambda: pressed_at.setdefault("t", time.perf_counter() - start))
        returned = time.perf_counter() - start
    finally:
        mic.close()
    assert pressed_at["t"] - 0.3 <= 0.15
    assert returned - 1.3 <= 0.15
    seconds = wav_seconds(clip.wav)
    assert 0.85 <= seconds <= 1.2
    assert clip.seconds == pytest.approx(seconds)


@needs_mic
def test_level_meter_reports_levels():
    meter = audio.LevelMeter()
    try:
        time.sleep(0.3)
        assert 0.0 <= meter.level <= 1.0
    finally:
        meter.close()
