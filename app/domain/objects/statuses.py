from enum import Enum


class ObjectStatus(str, Enum):
    WAITING = "waiting"
    ACTIVE = "active"
    COMPLETED = "completed"

    @property
    def label(self) -> str:
        return {
            ObjectStatus.WAITING: "В Ожидании",
            ObjectStatus.ACTIVE: "Действующий",
            ObjectStatus.COMPLETED: "Завершенный",
        }[self]
