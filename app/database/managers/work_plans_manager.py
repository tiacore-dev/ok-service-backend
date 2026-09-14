from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import and_, asc, desc

from app.database.managers.abstract_manager import BaseDBManager
from app.database.models import WorkPlans


class WorkPlansManager(BaseDBManager):
    @property
    def model(self):
        return WorkPlans

    def get_all_filtered(
        self,
        offset: int = 0,
        limit: int | None = 1000,
        sort_by: str = "date",
        sort_order: str = "asc",
        **filters: Any,
    ) -> list[dict[str, Any]]:
        with self.session_scope() as session:
            query = session.query(self.model)
            conditions = []
            year = filters.pop("year", None)
            user_id_is_null = filters.pop("user_id_is_null", None)
            if year is not None:
                conditions.extend((self.model.date >= date(year, 1, 1), self.model.date < date(year + 1, 1, 1)))
            if user_id_is_null is True:
                conditions.append(self.model.user_id.is_(None))
            elif user_id_is_null is False:
                conditions.append(self.model.user_id.is_not(None))
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    conditions.append(getattr(self.model, key) == value)
            if conditions:
                query = query.filter(and_(*conditions))
            if hasattr(self.model, sort_by):
                query = query.order_by((desc if sort_order == "desc" else asc)(getattr(self.model, sort_by)))
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            return [record.to_dict() for record in query.all()]

    def update(self, record_id: UUID, **kwargs: object) -> dict[str, Any] | None:
        with self.session_scope() as session:
            record = (
                session.query(self.model)
                .filter(self.model.work_plan_id == record_id)
                .first()
            )
            if record is None:
                return None
            for key, value in kwargs.items():
                if hasattr(self.model, key):
                    setattr(record, key, value)
            session.flush()
            return record.to_dict()
