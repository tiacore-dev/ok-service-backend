from __future__ import annotations

from dataclasses import dataclass
@dataclass(frozen=True, slots=True)
class ObjectStatus:
    object_status_id: str
    name: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", str(self.name).strip())
