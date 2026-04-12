from enum import Enum


class ControllerType(str, Enum):
    X360 = "x360"
    DS4 = "ds4"

    @property
    def label(self):
        return {"x360": "X360", "ds4": "DS4"}[self.value]

    @property
    def is_virtual(self):
        return True
