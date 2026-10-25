import json

from src.constants import crewchief_number
from src.crewchief_actions import vjoy_actions


def write_install(path):
    """The two CrewChief files that hold the names its controller list shows."""
    (path / "ui_text").mkdir(parents=True)
    (path / "ui_text" / "en.txt").write_text(
        "# comment\nvolume_down = Decrease messages volume\nmessages_volume = &Messages volume\n", encoding="utf-8")
    (path / "speech_recognition_config.txt").write_text(
        "# comment\nDO_I_HAVE_A_PENALTY = do I have a penalty\n"
        "RADIO_CHECK = can you hear me:radio check\n", encoding="utf-8")


def write_settings(path, assignments):
    devices = [{"deviceName": "vJoy Device", "guid": "vjoy-guid"}, {"deviceName": "Wheel", "guid": "wheel-guid"}]
    path.write_text(json.dumps({"devices": devices, "buttonAssignments": assignments}), encoding="utf-8")


def assignment(action, index, guid="vjoy-guid", pov=False):
    return {"action": action, "deviceGuid": guid, "buttonIndex": index, "usePovData": pov, "povValue": 0}


def test_names_and_numbers_match_crewchief(tmp_path):
    install, settings = tmp_path / "CrewChiefV4", tmp_path / "defaultSettings.json"
    write_install(install)
    write_settings(settings, [
        assignment("volume_down", 1),
        assignment("DO_I_HAVE_A_PENALTY", 30),
        assignment("RADIO_CHECK", 32),
        assignment("HOWS_MY_FUEL", 12),          # not in the text files: falls back to the action id
        assignment("WHOS_LEADING", 5, guid="wheel-guid"),  # another device
        assignment("talk_to_crew_chief", 0, pov=True),     # a hat direction, not a button
        assignment("HOW_LONGS_LEFT", -1),        # not bound
    ])
    actions = vjoy_actions(str(settings), str(install))
    # Keyed by vJoy button; CrewChief shows each one 1 lower
    assert actions == {2: "Decrease messages volume", 31: "Do I have a penalty", 33: "Can you hear me",
                       13: "Hows my fuel"}
    assert crewchief_number(31) == 30


def test_unreadable_settings_and_no_vjoy(tmp_path):
    assert vjoy_actions(str(tmp_path / "missing.json"), str(tmp_path)) is None
    settings = tmp_path / "defaultSettings.json"
    settings.write_text(json.dumps({"devices": [{"deviceName": "Wheel", "guid": "w"}], "buttonAssignments": []}),
                        encoding="utf-8")
    assert vjoy_actions(str(settings), str(tmp_path)) == {}
