MAX_BUTTONS = 64
VJOY_DEVICE_ID = 1


def crewchief_number(button_key):
    """The number CrewChief shows for a vJoy button. CrewChief counts from 0, so vJoy button 31 is its 30."""
    return int(button_key) - 1
