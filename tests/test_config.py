import json
import os
import threading

import src.config_manager as cm


def test_first_run_does_not_mutate_defaults():
    cm.set_setting("audio.ptt_sound_enabled", False)
    assert cm.DEFAULTS["settings"]["audio"]["ptt_sound_enabled"] is True
    assert cm.get_setting("audio.ptt_sound_enabled") is False


def test_corrupt_file_is_moved_aside_and_defaults_restored():
    os.makedirs(os.path.dirname(cm.CONFIG_PATH), exist_ok=True)
    with open(cm.CONFIG_PATH, "w") as f:
        f.write('{"settings": {"ptt_key": "f')  # truncated mid-write
    assert cm.load_config()["settings"]["ptt_key"] == "scroll lock"
    folder = os.path.dirname(cm.CONFIG_PATH)
    assert any(".broken_" in name for name in os.listdir(folder))
    with open(cm.CONFIG_PATH, encoding="utf-8") as f:
        json.load(f)


def test_non_dict_config_is_replaced():
    os.makedirs(os.path.dirname(cm.CONFIG_PATH), exist_ok=True)
    with open(cm.CONFIG_PATH, "w") as f:
        f.write("[]")
    assert cm.load_config()["settings"]["ptt_key"] == "scroll lock"


def test_save_is_atomic():
    cm.set_setting("ptt_key", "f9")
    assert not os.path.exists(cm.CONFIG_PATH + ".tmp")
    assert cm.get_setting("ptt_key") == "f9"


def test_concurrent_reads_never_see_a_half_written_file():
    errors, stop = [], threading.Event()

    def reader():
        while not stop.is_set():
            try:
                cm.get_setting("confidence_threshold")
                cm.get_all_commands()
            except Exception as e:
                errors.append(repr(e))

    thread = threading.Thread(target=reader)
    thread.start()
    for i in range(200):
        cm.set_setting("confidence_threshold", i % 100)
    stop.set()
    thread.join()
    assert not errors


def test_new_configs_have_no_api_key_field():
    assert "openai_api_key" not in cm.DEFAULTS["settings"]
