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


@needs_mic
def test_pre_roll_keeps_audio_from_before_the_press():
    mic = audio.Microphone()
    try:
        time.sleep(0.6)
        mic.start_recording()
        time.sleep(0.5)
        pcm = mic.stop_recording()
    finally:
        mic.close()
    seconds = len(pcm) / 2 / audio.SAMPLE_RATE
    assert 0.78 <= seconds <= 0.95  # 0.3 s pre-roll + 0.5 s held + delivery tail


@needs_mic
def test_record_command_follows_the_key(monkeypatch):
    monkeypatch.setattr(audio, "play_ptt_on", lambda: None)
    monkeypatch.setattr(audio, "play_ptt_off", lambda: None)
    start = time.perf_counter()
    monkeypatch.setattr(audio.keyboard, "is_pressed", lambda key: 0.3 <= time.perf_counter() - start < 1.3)
    pressed_at = {}
    mic = audio.Microphone()
    try:
        buf = audio.record_command(mic, "f8", threading.Event(),
                                   on_start=lambda: pressed_at.setdefault("t", time.perf_counter() - start))
        returned = time.perf_counter() - start
    finally:
        mic.close()
    assert pressed_at["t"] - 0.3 <= 0.05
    assert returned - 1.3 <= 0.15
    assert 1.2 <= wav_seconds(buf) <= 1.45


@needs_mic
def test_level_meter_reports_levels():
    meter = audio.LevelMeter()
    try:
        time.sleep(0.3)
        assert 0.0 <= meter.level <= 1.0
    finally:
        meter.close()
