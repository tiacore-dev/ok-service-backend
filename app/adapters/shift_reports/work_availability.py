from __future__ import annotations

from collections.abc import Collection, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session as OrmSession

from app.adapters._typing import require_uuid
from app.database import db_globals
from app.database.models import ShiftReports, Users, WorkPrices
from app.domain.work_prices import UNAVAILABLE_WORK_PRICE
from app.use_cases.shift_reports.ports import ShiftWorkAvailabilityReader


@dataclass(slots=True)
class SQLAlchemyShiftWorkAvailabilityReader(ShiftWorkAvailabilityReader):
    """Read-only queries for the shift work availability rule (no N+1)."""

    session: OrmSession | None = None

    @contextmanager
    def _session(self) -> Iterator[OrmSession]:
        if self.session is not None:
            yield self.session
            return
        session_factory = db_globals.Session
        if session_factory is None:
            raise RuntimeError("Database session is not initialized")
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    def get_shift_report_performer_category(
        self, shift_report_id: UUID
    ) -> int | None:
        with self._session() as session:
            row = (
                session.query(Users.category)
                .join(ShiftReports, ShiftReports.user == Users.user_id)
                .filter(ShiftReports.shift_report_id == shift_report_id)
                .first()
            )
            return int(row[0]) if row is not None else None

    def get_user_categories(self, user_ids: Collection[UUID]) -> dict[UUID, int]:
        if not user_ids:
            return {}
        with self._session() as session:
            rows = (
                session.query(Users.user_id, Users.category)
                .filter(Users.user_id.in_(list(user_ids)))
                .all()
            )
            return {
                require_uuid(user_id, "user_id"): int(category)
                for user_id, category in rows
            }

    def get_unavailable_work_ids(
        self, work_ids: Collection[UUID], category: int
    ) -> set[UUID]:
        if not work_ids:
            return set()
        with self._session() as session:
            rows = (
                session.query(WorkPrices.work)
                .filter(
                    WorkPrices.work.in_(list(work_ids)),
                    WorkPrices.category == category,
                    WorkPrices.deleted.is_(False),
                    WorkPrices.price == UNAVAILABLE_WORK_PRICE,
                )
                .distinct()
                .all()
            )
            return {require_uuid(work_id, "work") for (work_id,) in rows}
