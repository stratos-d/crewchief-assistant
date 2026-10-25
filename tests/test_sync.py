import json

import src.config_manager as cm
from src.crewchief_sync import sync_crewchief_config, sees_vjoy


def write_crewchief_settings(path, n_actions, with_vjoy=True):
    devices = [{"deviceName": "Wheel", "guid": "wheel-guid"}]
    if with_vjoy:
        devices.insert(0, {"deviceName": "vJoy Device", "guid": "vjoy-guid"})
    data = {
        "devices": devices,
        "buttonAssignments": [{"action": f"ACTION_{i}", "deviceGuid": "", "buttonIndex": -1, "usePovData": False,
                               "povValue": 0, "availableAction": True} for i in range(n_actions)],
    }
    path.write_text(json.dumps(data), encoding="utf-8")


def test_resync_clears_buttons_no_longer_used(tmp_path):
    settings = tmp_path / "defaultSettings.json"
    controllers = cm.load_config()["controllers"]
    controllers[0]["bindings"]["30"] = {"command": "old manual command", "enabled": True}

    write_crewchief_settings(settings, 10)
    first = sync_crewchief_config(str(settings), controllers)
    bindings = first["bindings"][0]["bindings"]
    assert all(bindings[str(i)]["enabled"] for i in range(1, 11))
    assert bindings["30"] == {"command": "", "enabled": False}

    write_crewchief_settings(settings, 5)
    second = sync_crewchief_config(str(settings), first["bindings"])
    bindings = second["bindings"][0]["bindings"]
    assert sorted(int(k) for k, v in bindings.items() if v["enabled"]) == [1, 2, 3, 4, 5]
    assert len(bindings) == 64


def test_sync_writes_a_backup(tmp_path):
    settings = tmp_path / "defaultSettings.json"
    write_crewchief_settings(settings, 3)
    sync_crewchief_config(str(settings), cm.load_config()["controllers"])
    assert any(".backup_" in p.name for p in tmp_path.iterdir())


def test_sees_vjoy(tmp_path):
    settings = tmp_path / "defaultSettings.json"
    assert not sees_vjoy(str(settings))  # missing file
    write_crewchief_settings(settings, 3, with_vjoy=False)
    assert not sees_vjoy(str(settings))
    write_crewchief_settings(settings, 3, with_vjoy=True)
    assert sees_vjoy(str(settings))
