from uuid import UUID

from sqlalchemy import and_

from app.database.managers.abstract_manager import BaseDBManager
from app.database.models import Leaves, ShiftReports, AbsenceReason


class LeavesManager(BaseDBManager):

    @property
    def model(self):
        return Leaves

    def _to_uuid(self, value):
        if isinstance(value, str):
            return UUID(value)
        return value

    def has_shift_conflict(self, user_id, start_date, end_date, session=None):
        user_uuid = self._to_uuid(user_id)
        if session is None:
            with self.session_scope() as scoped_session:
                return self._has_shift_conflict(scoped_session, user_uuid, start_date, end_date)
        return self._has_shift_conflict(session, user_uuid, start_date, end_date)

    def _has_shift_conflict(self, session, user_uuid, start_date, end_date):
        exists = (
            session.query(ShiftReports)
            .filter(
                ShiftReports.user == user_uuid,
                ShiftReports.deleted.is_(False),
                ShiftReports.date >= start_date,
                ShiftReports.date <= end_date,
            )
            .first()
        )
        return exists is not None

    def has_overlapping_leave(self, user_id, start_date, end_date, exclude_id=None, session=None):
        user_uuid = self._to_uuid(user_id)
        exclude_uuid = self._to_uuid(exclude_id) if exclude_id else None

        if session is None:
            with self.session_scope() as scoped_session:
                return self._has_overlapping_leave(
                    scoped_session, user_uuid, start_date, end_date, exclude_uuid
                )
        return self._has_overlapping_leave(
            session, user_uuid, start_date, end_date, exclude_uuid
        )

    def _has_overlapping_leave(self, session, user_uuid, start_date, end_date, exclude_uuid):
        filters = [
            Leaves.user_id == user_uuid,
            Leaves.deleted.is_(False),
            Leaves.start_date <= end_date,
            Leaves.end_date >= start_date,
        ]
        if exclude_uuid:
            filters.append(Leaves.leave_id != exclude_uuid)

        exists = session.query(Leaves).filter(and_(*filters)).first()
        return exists is not None

    def add_leave(self, **kwargs):
        reason = kwargs.pop("reason")
        kwargs["reason"] = AbsenceReason(reason) if not isinstance(reason, AbsenceReason) else reason
        kwargs["user_id"] = self._to_uuid(kwargs.get("user_id"))
        kwargs["responsible_id"] = self._to_uuid(kwargs.get("responsible_id"))
        kwargs["created_by"] = self._to_uuid(kwargs.get("created_by"))
        if kwargs.get("updated_by"):
            kwargs["updated_by"] = self._to_uuid(kwargs.get("updated_by"))
        return self.add(**kwargs)

    def update_leave(self, leave_id, **kwargs):
        if "reason" in kwargs and kwargs["reason"] is not None:
            kwargs["reason"] = AbsenceReason(kwargs["reason"])
        if "user_id" in kwargs and kwargs["user_id"] is not None:
            kwargs["user_id"] = self._to_uuid(kwargs["user_id"])
        if "responsible_id" in kwargs and kwargs["responsible_id"] is not None:
            kwargs["responsible_id"] = self._to_uuid(kwargs["responsible_id"])
        if "created_by" in kwargs and kwargs["created_by"] is not None:
            kwargs["created_by"] = self._to_uuid(kwargs["created_by"])
        if "updated_by" in kwargs and kwargs["updated_by"] is not None:
            kwargs["updated_by"] = self._to_uuid(kwargs["updated_by"])
        return self.update(self._to_uuid(leave_id), **kwargs)

    def list_leaves(
        self,
        offset=0,
        limit=None,
        sort_by="created_at",
        sort_order="desc",
        **filters,
    ):
        user_filter = filters.get("user_id") or filters.get("user")
        responsible_filter = filters.get("responsible_id") or filters.get("responsible")
        reason_filter = filters.get("reason")
        deleted_filter = filters.get("deleted")
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")

        with self.session_scope() as session:
            query = session.query(Leaves)

            if user_filter:
                query = query.filter(Leaves.user_id == self._to_uuid(user_filter))
            if responsible_filter:
                query = query.filter(
                    Leaves.responsible_id == self._to_uuid(responsible_filter)
                )
            if reason_filter:
                query = query.filter(Leaves.reason == AbsenceReason(reason_filter))
            if deleted_filter is not None:
                query = query.filter(Leaves.deleted == deleted_filter)

            if date_from is not None and date_to is not None:
                query = query.filter(Leaves.start_date <= date_to, Leaves.end_date >= date_from)
            elif date_from is not None:
                query = query.filter(Leaves.end_date >= date_from)
            elif date_to is not None:
                query = query.filter(Leaves.start_date <= date_to)

            if sort_by and hasattr(Leaves, sort_by):
                order_attr = getattr(Leaves, sort_by)
                query = query.order_by(
                    order_attr.desc() if sort_order == "desc" else order_attr.asc()
                )

            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)

            return [leave.to_dict() for leave in query.all()]
