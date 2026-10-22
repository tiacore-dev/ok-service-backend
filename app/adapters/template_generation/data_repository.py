"""Read printable snapshots while the ORM session is open; never expose ORM objects."""

from typing import Any, cast
from uuid import UUID

from marshmallow import ValidationError
from sqlalchemy.orm import joinedload, selectinload

from app.database import db_globals
from app.database.models import Leaves, Projects, ShiftReports, Users, Works
from app.database.models.project_materials import ProjectMaterials
from app.database.models.shift_report_details import ShiftReportDetails
from app.database.models.shift_report_materials import ShiftReportMaterials
from app.domain.template_generation import TemplateGenerationError
from app.domain.templates import TemplateTypes
from app.schemas.template_data_schemas import (
    ShiftReportRegistryPrintSchema,
    template_data_schema,
)
from app.use_cases.template_generation.dto import GenerationParameters, ShiftData


def fields_of(model: Any, *names: str) -> dict[str, Any]:
    return {name: getattr(model, name) for name in names}


def user_data(model: Any) -> dict[str, Any] | None:
    return fields_of(model, "user_id", "name", "login") if model is not None else None


def work_data(model: Any) -> dict[str, Any]:
    return dict(
        fields_of(model, "work_id", "name"),
        category=fields_of(model.work_category, "work_category_id", "name")
        if model.work_category is not None
        else None,
        measurement_unit=unit_data(model.measurement_unit_ref),
        work_prices=[
            fields_of(row, "work_price_id", "category", "price")
            for row in sorted(
                model.work_price, key=lambda row: (row.category, str(row.work_price_id))
            )
        ],
    )


def unit_data(model: Any) -> dict[str, Any] | None:
    return (
        fields_of(model, "measurement_unit_id", "name") if model is not None else None
    )


def project_work_data(model: Any) -> dict[str, Any] | None:
    return (
        fields_of(model, "project_work_id", "project_work_name", "price")
        if model is not None
        else None
    )


def project_material_data(model: Any) -> dict[str, Any]:
    material = model.materials
    return dict(
        fields_of(model, "project_material_id", "project_material_name", "price"),
        material=dict(
            fields_of(material, "material_id", "name"),
            measurement_unit=unit_data(material.measurement_unit_ref),
        ),
    )


def shift_data(model: Any) -> ShiftData:
    nested = {
        "user",
        "project",
        "object",
        "signed_by",
        "updated_by",
        "shift_report_details_sum",
        "shift_report_details_summ_by_estimate",
    }
    registry = fields_of(
        model,
        *(
            name
            for name in ShiftReportRegistryPrintSchema().fields
            if name not in nested
        ),
    )
    registry.update(
        user=user_data(model.users),
        project=fields_of(model.projects, "project_id", "name"),
        object=fields_of(model.projects.objects, "object_id", "name", "address"),
        signed_by=user_data(model.signed_by_user),
        updated_by=user_data(model.updated_by_user),
    )
    return ShiftData(
        registry=registry,
        details=[
            dict(
                fields_of(row, "shift_report_detail_id", "quantity", "summ"),
                work=work_data(row.works),
                project_work=project_work_data(row.project_works),
            )
            for row in sorted(
                model.shift_report_details,
                key=lambda row: str(row.shift_report_detail_id),
            )
        ],
        materials=[
            dict(
                fields_of(
                    row, "shift_report_material_id", "quantity", "shift_report_detail"
                ),
                project_material=project_material_data(row.project_materials),
            )
            for row in sorted(
                model.shift_report_materials,
                key=lambda row: str(row.shift_report_material_id),
            )
        ],
    )


class MarshmallowDocumentDataSerializer:
    def serialize(
        self, template_type: TemplateTypes, data: dict[str, Any]
    ) -> dict[str, Any]:
        schema = template_data_schema(template_type)
        result = schema.dump(data)
        if not isinstance(result, dict):
            raise TemplateGenerationError("Printable data must be an object")
        printable_data = cast(dict[str, Any], result)
        # dump does not validate. Also check required fields and scalar constraints.
        try:
            schema.load(printable_data)
        except ValidationError as error:
            raise TemplateGenerationError(
                "Printable data does not match the template schema"
            ) from error
        return printable_data


class SQLAlchemyDocumentDataRepository:
    @staticmethod
    def _session():
        if db_globals.Session is None:
            raise RuntimeError("Database session is not initialized")
        return db_globals.Session()

    def works(self) -> list[dict[str, Any]]:
        session = self._session()
        try:
            # No new catalog filters: the existing unfiltered
            # registry includes deleted entries.
            rows = (
                session.query(Works)
                .options(selectinload(Works.work_price))
                .order_by(Works.name, Works.work_id)
                .all()
            )
            return [work_data(row) for row in rows]
        finally:
            session.close()

    def shifts(
        self, parameters: GenerationParameters, start: int | None, end: int | None
    ) -> list[ShiftData]:
        session = self._session()
        try:
            query = (
                session.query(ShiftReports)
                .options(
                    joinedload(ShiftReports.users),
                    joinedload(ShiftReports.projects).joinedload(Projects.objects),
                    joinedload(ShiftReports.signed_by_user),
                    joinedload(ShiftReports.updated_by_user),
                    selectinload(ShiftReports.shift_report_details)
                    .joinedload(ShiftReportDetails.works)
                    .selectinload(Works.work_price),
                    selectinload(ShiftReports.shift_report_details).joinedload(
                        ShiftReportDetails.project_works
                    ),
                    selectinload(ShiftReports.shift_report_materials)
                    .joinedload(ShiftReportMaterials.project_materials)
                    .joinedload(ProjectMaterials.materials),
                )
                .filter(
                    ShiftReports.signed.is_(True),
                    ShiftReports.deleted.is_(False),
                    ShiftReports.leave_id.is_(None),
                )
            )
            if parameters.shift_report_id is not None:
                query = query.filter(
                    ShiftReports.shift_report_id == parameters.shift_report_id
                )
            if start is not None and end is not None:
                query = query.filter(
                    ShiftReports.date >= start, ShiftReports.date < end
                )
            if parameters.user is not None:
                query = query.filter(ShiftReports.user == parameters.user)
            if parameters.users:
                query = query.filter(ShiftReports.user.in_(parameters.users))
            if parameters.projects:
                query = query.filter(ShiftReports.project.in_(parameters.projects))
            return [
                shift_data(row)
                for row in query.order_by(
                    ShiftReports.date, ShiftReports.number, ShiftReports.shift_report_id
                ).all()
            ]
        finally:
            session.close()

    def _references(
        self, model, key: str, ids: tuple[UUID, ...], columns: tuple[str, ...]
    ) -> list[dict[str, Any]]:
        if not ids:
            return []
        session = self._session()
        try:
            rows = session.query(model).filter(getattr(model, key).in_(ids)).all()
            by_id = {getattr(row, key): fields_of(row, *columns) for row in rows}
            if set(ids) - by_id.keys():
                raise ValueError(f"Не найдены значения параметра {key}")
            return [by_id[identifier] for identifier in dict.fromkeys(ids)]
        finally:
            session.close()

    def users(self, ids: tuple[UUID, ...]) -> list[dict[str, Any]]:
        return self._references(Users, "user_id", ids, ("user_id", "name", "login"))

    def projects(self, ids: tuple[UUID, ...]) -> list[dict[str, Any]]:
        return self._references(Projects, "project_id", ids, ("project_id", "name"))

    def leaves(self, user: UUID, start: int, end: int) -> list[dict[str, Any]]:
        session = self._session()
        try:
            rows = (
                session.query(Leaves)
                .filter(
                    Leaves.user_id == user,
                    Leaves.deleted.is_(False),
                    Leaves.start_date < end,
                    Leaves.end_date >= start,
                )
                .order_by(Leaves.start_date, Leaves.leave_id)
                .all()
            )
            return [
                dict(
                    fields_of(row, "leave_id", "start_date", "end_date", "comment"),
                    reason=row.reason.value,
                    reason_label=row.reason.label(),
                )
                for row in rows
            ]
        finally:
            session.close()
