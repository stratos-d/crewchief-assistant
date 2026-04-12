from dataclasses import dataclass, field
from src.constants import ControllerType


@dataclass
class Controller:
    name: str
    type: ControllerType
    bindings: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Controller":
        return cls(
            name=data.get("name", "Controller"),
            type=ControllerType(data.get("type", ControllerType.X360)),
            bindings=data.get("bindings", {}),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type.value,
            "bindings": self.bindings,
        }
