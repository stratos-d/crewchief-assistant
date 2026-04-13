from dataclasses import dataclass, field


@dataclass
class Controller:
    name: str
    bindings: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Controller":
        return cls(
            name=data.get("name", "Controller"),
            bindings=data.get("bindings", {}),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "bindings": self.bindings,
        }
