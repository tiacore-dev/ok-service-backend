from enum import Enum


class ProjectStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WORKS_COMPLETED = "works_completed"
    CLOSED = "closed"

    @property
    def label(self) -> str:
        return {
            ProjectStatus.PENDING: "На согласовании",
            ProjectStatus.IN_PROGRESS: "В работе",
            ProjectStatus.WORKS_COMPLETED: "Работы выполнены",
            ProjectStatus.CLOSED: "Закрыто",
        }[self]

    @classmethod
    def neighbours(cls, status: "ProjectStatus") -> tuple["ProjectStatus", ...]:
        order = tuple(cls)
        index = order.index(status)
        return tuple(
            item for item in (order[index - 1] if index else None,
                              order[index + 1] if index + 1 < len(order) else None)
            if item is not None
        )
