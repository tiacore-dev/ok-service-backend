import logging
import secrets

from app.database.managers.abstract_manager import BaseDBManager
from app.database.models import ApiKeys

logger = logging.getLogger("ok_service")


class ApiKeysManager(BaseDBManager):
    @property
    def model(self):
        return ApiKeys

    def generate_api_key(self, name, expires_at):
        with self.session_scope() as session:
            token = self._generate_unique_token(session)
            api_key = self.model(name=name, token=token, expires_at=expires_at)
            session.add(api_key)
            session.flush()
            return {
                "api_key_id": str(api_key.api_key_id),
                "token": token,
            }

    def get_by_id_public(self, api_key_id):
        with self.session_scope() as session:
            record = session.query(self.model).filter_by(api_key_id=api_key_id).first()
            if not record:
                return None
            return record.to_public_dict()

    def get_all_public(self, offset=0, limit=None, sort_by="created_at", sort_order="desc"):
        records = self.get_all_filtered(
            offset=offset,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        return [record.to_public_dict() for record in records]

    def _generate_unique_token(self, session):
        for _ in range(10):
            token = secrets.token_urlsafe(48)
            exists = session.query(self.model).filter_by(token=token).first()
            if not exists:
                return token
        raise RuntimeError("Failed to generate unique API key token")
