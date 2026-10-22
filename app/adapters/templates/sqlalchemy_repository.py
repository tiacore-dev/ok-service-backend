from dataclasses import asdict
from typing import NoReturn, cast
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.database import db_globals
from app.database.models.templates import Templates
from app.domain.templates import (
    DEFAULT_TEMPLATE_INDEX,
    Template,
    TemplateConflictError,
    TemplateNotFoundError,
    TemplateTypes,
)
from app.use_cases.templates.dto import TemplateFileChanges


class SQLAlchemyTemplateRepository:
    @staticmethod
    def _session():
        if db_globals.Session is None:
            raise RuntimeError("Database session is not initialized")
        return db_globals.Session()

    @staticmethod
    def _template(model: Templates) -> Template:
        # ORM attributes are validated by the table's non-null/type constraints.
        return Template(
            **{key: getattr(model, key) for key in Template.__dataclass_fields__}
        )

    @staticmethod
    def _map_integrity(error: IntegrityError) -> NoReturn:
        if DEFAULT_TEMPLATE_INDEX in str(error.orig):
            raise TemplateConflictError(
                "Для этого типа уже назначен шаблон по умолчанию"
            ) from error
        raise error

    def create(self, template: Template) -> None:
        session = self._session()
        try:
            session.add(Templates(**asdict(template)))
            session.commit()
        except IntegrityError as error:
            session.rollback()
            self._map_integrity(error)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get(self, template_id: UUID) -> Template:
        session = self._session()
        try:
            model = session.get(Templates, template_id)
            if model is None:
                raise TemplateNotFoundError("Template not found")
            return self._template(model)
        finally:
            session.close()

    def get_default(self, template_type: TemplateTypes) -> Template | None:
        session = self._session()
        try:
            model = session.query(Templates).filter(
                Templates.template_type == template_type,
                Templates.is_default.is_(True),
            ).one_or_none()
            return self._template(model) if model is not None else None
        finally:
            session.close()

    def list(
        self, template_type: TemplateTypes | None, offset: int, limit: int
    ) -> list[Template]:
        session = self._session()
        try:
            query = session.query(Templates)
            if template_type is not None:
                query = query.filter(Templates.template_type == template_type)
            return [
                self._template(model)
                for model in query.order_by(Templates.name, Templates.id)
                .offset(offset)
                .limit(limit)
                .all()
            ]
        finally:
            session.close()

    def update(
        self, template_id: UUID, changes: TemplateFileChanges
    ) -> tuple[Template, str | None]:
        session = self._session()
        try:
            model = (
                session.query(Templates)
                .filter(Templates.id == template_id)
                .with_for_update()
                .first()
            )
            if model is None:
                raise TemplateNotFoundError("Template not found")
            old_key = cast(str, model.s3_key) if "s3_key" in changes else None
            for key, value in changes.items():
                setattr(model, key, value)
            session.flush()
            result = self._template(model)
            session.commit()
            return result, old_key
        except IntegrityError as error:
            session.rollback()
            self._map_integrity(error)
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def delete(self, template_id: UUID) -> Template:
        session = self._session()
        try:
            model = (
                session.query(Templates)
                .filter(Templates.id == template_id)
                .with_for_update()
                .first()
            )
            if model is None:
                raise TemplateNotFoundError("Template not found")
            result = self._template(model)
            session.delete(model)
            session.commit()
            return result
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
