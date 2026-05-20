from app.database.managers.abstract_manager import BaseDBManager
from app.database.models import KeyPermissionTypeRelations, PermissionTypes


class KeyPermissionTypeRelationsManager(BaseDBManager):
    @property
    def model(self):
        return KeyPermissionTypeRelations

    def add_many(self, api_key_id, permission_type_ids):
        created = []
        with self.session_scope() as session:
            for permission_type_id in permission_type_ids:
                relation = self.model(
                    api_key_id=api_key_id, permission_type_id=permission_type_id
                )
                session.add(relation)
                session.flush()
                created.append(relation.to_dict())
        return created

    def get_permission_types_all(
        self, offset=0, limit=None, sort_by="code", sort_order="asc"
    ):
        with self.session_scope() as session:
            query = session.query(PermissionTypes)
            if sort_by and hasattr(PermissionTypes, sort_by):
                column = getattr(PermissionTypes, sort_by)
                query = query.order_by(
                    column.asc() if sort_order == "asc" else column.desc()
                )
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            rows = query.all()
            return [row.to_dict() for row in rows]
