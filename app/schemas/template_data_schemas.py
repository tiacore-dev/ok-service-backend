"""Contracts for printable data. No database access or report generation."""

from typing import Any

from marshmallow import Schema, ValidationError, fields, validate, validates_schema

from app.domain.template_generation.period import validate_report_period_end
from app.domain.templates import TemplateTypes


def meta(title: str, example: Any) -> dict[str, Any]:
    return {"title": title, "example": example}


class PrintSchema(Schema):
    """Unknown fields are rejected, including private ORM/user attributes."""


class UserPrintSchema(PrintSchema):
    user_id = fields.UUID(
        required=True,
        metadata=meta("ID исполнителя", "00000000-0000-0000-0000-000000000001"),
    )
    name = fields.String(
        required=True, metadata=meta("ФИО исполнителя", "Иванов Иван Иванович")
    )
    login = fields.String(required=True, metadata=meta("Логин", "employee"))


class MeasurementUnitPrintSchema(PrintSchema):
    measurement_unit_id = fields.UUID(
        required=True,
        metadata=meta("ID единицы измерения", "00000000-0000-0000-0000-000000000002"),
    )
    name = fields.String(required=True, metadata=meta("Единица измерения", "м²"))


class WorkCategoryPrintSchema(PrintSchema):
    work_category_id = fields.UUID(
        required=True,
        metadata=meta("ID категории работы", "00000000-0000-0000-0000-000000000003"),
    )
    name = fields.String(
        required=True, metadata=meta("Категория работы", "Монтажные работы")
    )


class WorkPricePrintSchema(PrintSchema):
    work_price_id = fields.UUID(
        required=True,
        metadata=meta("ID расценки", "00000000-0000-0000-0000-000000000004"),
    )
    category = fields.Integer(
        required=True, validate=validate.Range(min=0, max=4), metadata=meta("Разряд", 0)
    )
    price = fields.Float(required=True, metadata=meta("Расценка", 150.25))


class WorkPrintSchema(PrintSchema):
    work_id = fields.UUID(
        required=True,
        metadata=meta("ID работы каталога", "00000000-0000-0000-0000-000000000005"),
    )
    name = fields.String(
        required=True, metadata=meta("Наименование работы", "Монтаж конструкции")
    )
    category = fields.Nested(
        WorkCategoryPrintSchema,
        required=True,
        allow_none=True,
        metadata=meta("Категория работы", None),
    )
    measurement_unit = fields.Nested(
        MeasurementUnitPrintSchema,
        required=True,
        allow_none=True,
        metadata=meta("Единица измерения работы", None),
    )
    work_prices = fields.List(
        fields.Nested(WorkPricePrintSchema),
        required=True,
        metadata=meta("Расценки работы по разрядам", []),
    )


class MaterialPrintSchema(PrintSchema):
    material_id = fields.UUID(
        required=True,
        metadata=meta("ID материала каталога", "00000000-0000-0000-0000-000000000006"),
    )
    name = fields.String(
        required=True, metadata=meta("Наименование материала", "Крепёж")
    )
    measurement_unit = fields.Nested(
        MeasurementUnitPrintSchema,
        required=True,
        allow_none=True,
        metadata=meta("Единица измерения материала", None),
    )


class ObjectPrintSchema(PrintSchema):
    object_id = fields.UUID(
        required=True,
        metadata=meta("ID объекта", "00000000-0000-0000-0000-000000000007"),
    )
    name = fields.String(required=True, metadata=meta("Название объекта", "Объект № 1"))
    address = fields.String(
        required=True,
        allow_none=True,
        metadata=meta("Адрес объекта", "Примерная улица, 1"),
    )


class ProjectPrintSchema(PrintSchema):
    project_id = fields.UUID(
        required=True,
        metadata=meta("ID спецификации", "00000000-0000-0000-0000-000000000008"),
    )
    name = fields.String(
        required=True, metadata=meta("Название спецификации", "Спецификация № 1")
    )


class ProjectWorkPrintSchema(PrintSchema):
    project_work_id = fields.UUID(
        required=True,
        metadata=meta(
            "ID позиции спецификации", "00000000-0000-0000-0000-000000000009"
        ),
    )
    project_work_name = fields.String(
        required=True,
        allow_none=True,
        metadata=meta("Наименование позиции спецификации", "Монтаж по спецификации"),
    )
    price = fields.Float(
        required=True,
        allow_none=True,
        metadata=meta("Цена работы по спецификации", 150.25),
    )


class ProjectMaterialPrintSchema(PrintSchema):
    project_material_id = fields.UUID(
        required=True,
        metadata=meta(
            "ID материала спецификации", "00000000-0000-0000-0000-000000000010"
        ),
    )
    project_material_name = fields.String(
        required=True,
        allow_none=True,
        metadata=meta("Наименование материала спецификации", "Крепёж по спецификации"),
    )
    material = fields.Nested(
        MaterialPrintSchema, required=True, metadata=meta("Материал каталога", {})
    )
    price = fields.Float(
        required=True,
        allow_none=True,
        metadata=meta("Цена материала по спецификации", 25.5),
    )


class ShiftReportDetailPrintSchema(PrintSchema):
    shift_report_detail_id = fields.UUID(
        required=True,
        metadata=meta("ID детали смены", "00000000-0000-0000-0000-000000000011"),
    )
    work = fields.Nested(
        WorkPrintSchema, required=True, metadata=meta("Работа каталога", {})
    )
    project_work = fields.Nested(
        ProjectWorkPrintSchema,
        required=True,
        allow_none=True,
        metadata=meta("Позиция спецификации", None),
    )
    quantity = fields.Float(required=True, metadata=meta("Выполненное количество", 2.5))
    summ = fields.Float(required=True, metadata=meta("Сохранённая сумма детали", 350.0))
    summ_by_estimate = fields.Float(
        required=True,
        allow_none=True,
        metadata=meta("Стоимость детали по спецификации", 375.625),
    )


class ShiftReportMaterialPrintSchema(PrintSchema):
    shift_report_material_id = fields.UUID(
        required=True,
        metadata=meta("ID расхода материала", "00000000-0000-0000-0000-000000000012"),
    )
    project_material = fields.Nested(
        ProjectMaterialPrintSchema,
        required=True,
        metadata=meta("Материал спецификации", {}),
    )
    shift_report_detail = fields.UUID(
        required=True, allow_none=True, metadata=meta("ID связанной детали смены", None)
    )
    quantity = fields.Float(required=True, metadata=meta("Расход материала", 3.0))
    summ_by_estimate = fields.Float(
        required=True,
        allow_none=True,
        metadata=meta("Стоимость расхода по спецификации", 76.5),
    )


class ShiftReportRegistryPrintSchema(PrintSchema):
    shift_report_id = fields.UUID(
        required=True,
        metadata=meta("ID сменного отчёта", "00000000-0000-0000-0000-000000000013"),
    )
    number = fields.Integer(required=True, metadata=meta("Номер смены", 123))
    user = fields.Nested(
        UserPrintSchema, required=True, metadata=meta("Исполнитель смены", {})
    )
    project = fields.Nested(
        ProjectPrintSchema, required=True, metadata=meta("Спецификация смены", {})
    )
    object = fields.Nested(
        ObjectPrintSchema, required=True, metadata=meta("Объект смены", {})
    )
    date = fields.Integer(
        required=True, metadata=meta("Дата смены, Unix мс", 1791133200000)
    )
    date_start = fields.Integer(
        required=True, allow_none=True, metadata=meta("Начало смены, Unix мс", None)
    )
    date_end = fields.Integer(
        required=True, allow_none=True, metadata=meta("Окончание смены, Unix мс", None)
    )
    lng_start = fields.Float(
        required=True, allow_none=True, metadata=meta("Долгота начала смены", None)
    )
    ltd_start = fields.Float(
        required=True, allow_none=True, metadata=meta("Широта начала смены", None)
    )
    lng_end = fields.Float(
        required=True, allow_none=True, metadata=meta("Долгота окончания смены", None)
    )
    ltd_end = fields.Float(
        required=True, allow_none=True, metadata=meta("Широта окончания смены", None)
    )
    distance_start = fields.Float(
        required=True, allow_none=True, metadata=meta("Расстояние при начале, м", None)
    )
    distance_end = fields.Float(
        required=True,
        allow_none=True,
        metadata=meta("Расстояние при окончании, м", None),
    )
    start_browser_id = fields.UUID(
        required=True, allow_none=True, metadata=meta("ID браузера начала смены", None)
    )
    finish_browser_id = fields.UUID(
        required=True,
        allow_none=True,
        metadata=meta("ID браузера окончания смены", None),
    )
    created_by = fields.UUID(
        required=True,
        metadata=meta("ID автора смены", "00000000-0000-0000-0000-000000000001"),
    )
    created_at = fields.Integer(
        required=True, metadata=meta("Создание смены, Unix мс", 1791133200000)
    )
    signed_at = fields.Integer(
        required=True,
        allow_none=True,
        metadata=meta("Согласование смены, Unix мс", None),
    )
    signed_by = fields.Nested(
        UserPrintSchema,
        required=True,
        allow_none=True,
        metadata=meta("Согласовавший смену", None),
    )
    updated_at = fields.Integer(
        required=True, allow_none=True, metadata=meta("Изменение смены, Unix мс", None)
    )
    updated_by = fields.Nested(
        UserPrintSchema,
        required=True,
        allow_none=True,
        metadata=meta("Изменивший смену", None),
    )
    signed = fields.Boolean(required=True, metadata=meta("Смена согласована", True))
    deleted = fields.Boolean(required=True, metadata=meta("Смена удалена", False))
    leave_id = fields.UUID(
        required=True,
        allow_none=True,
        metadata=meta("ID отсутствия, отменившего смену", None),
    )
    night_shift = fields.Boolean(required=True, metadata=meta("Ночная смена", False))
    extreme_conditions = fields.Boolean(
        required=True, metadata=meta("Экстремальные условия", False)
    )
    short_shift = fields.Boolean(required=True, metadata=meta("Короткая смена", False))
    comment = fields.String(
        required=True, allow_none=True, metadata=meta("Комментарий смены", None)
    )
    shift_report_details_sum = fields.Float(
        required=True, metadata=meta("Сумма сохранённых сумм деталей", 350.0)
    )
    shift_report_details_summ_by_estimate = fields.Float(
        required=True, metadata=meta("Стоимость смены по спецификации", 375.625)
    )


class ShiftReportWithDetailsPrintSchema(ShiftReportRegistryPrintSchema):
    shift_report_details = fields.List(
        fields.Nested(ShiftReportDetailPrintSchema),
        required=True,
        metadata=meta("Детали смены", []),
    )


class ShiftReportFullPrintSchema(ShiftReportWithDetailsPrintSchema):
    shift_report_materials = fields.List(
        fields.Nested(ShiftReportMaterialPrintSchema),
        required=True,
        metadata=meta("Материалы смены", []),
    )


class LeavePrintSchema(PrintSchema):
    leave_id = fields.UUID(
        required=True,
        metadata=meta("ID отсутствия", "00000000-0000-0000-0000-000000000014"),
    )
    start_date = fields.Integer(
        required=True, metadata=meta("Начало отсутствия, Unix мс", 1791133200000)
    )
    end_date = fields.Integer(
        required=True, metadata=meta("Конец отсутствия, Unix мс", 1791219600000)
    )
    reason = fields.String(
        required=True,
        validate=validate.OneOf(["vacation", "sick_leave", "day_off"]),
        metadata=meta("Причина отсутствия", "day_off"),
    )
    reason_label = fields.String(
        required=True, metadata=meta("Причина отсутствия по-русски", "Отгул")
    )
    comment = fields.String(
        required=True, allow_none=True, metadata=meta("Комментарий отсутствия", None)
    )


class PeriodSchema(PrintSchema):
    date_from = fields.Date(
        required=True, metadata=meta("Начало периода включительно", "2026-10-05")
    )
    date_to = fields.Date(
        required=True, metadata=meta("Конец периода включительно", "2026-10-06")
    )

    @validates_schema
    def validate_period(self, data, **kwargs):
        try:
            validate_report_period_end(data["date_to"])
        except ValueError as error:
            raise ValidationError(str(error), field_name="date_to") from error
        if data["date_from"] > data["date_to"]:
            raise ValidationError(
                "Конец периода не может быть раньше начала", field_name="date_to"
            )


class PayrollRequestSchema(PeriodSchema):
    user = fields.UUID(
        required=True,
        metadata=meta(
            "Единственный исполнитель", "00000000-0000-0000-0000-000000000001"
        ),
    )


class ObjectReportRequestSchema(PeriodSchema):
    users = fields.List(
        fields.UUID(),
        load_default=list,
        metadata=meta("Исполнители; пустой массив — без фильтра", []),
    )
    projects = fields.List(
        fields.UUID(),
        load_default=list,
        metadata=meta("Спецификации; пустой массив — без фильтра", []),
    )


class PayrollParametersPrintSchema(PeriodSchema):
    user = fields.Nested(
        UserPrintSchema, required=True, metadata=meta("Выбранный исполнитель", {})
    )


class ObjectReportParametersPrintSchema(PeriodSchema):
    users = fields.List(
        fields.Nested(UserPrintSchema),
        required=True,
        metadata=meta("Выбранные исполнители; пусто — без фильтра", []),
    )
    projects = fields.List(
        fields.Nested(ProjectPrintSchema),
        required=True,
        metadata=meta("Выбранные спецификации; пусто — без фильтра", []),
    )


class PayrollDayPrintSchema(PrintSchema):
    date = fields.Date(
        required=True, metadata=meta("Календарный день ведомости", "2026-10-05")
    )
    leave = fields.List(
        fields.Nested(LeavePrintSchema),
        required=True,
        metadata=meta("Отсутствия в этот день", []),
    )
    shift_report = fields.List(
        fields.Nested(ShiftReportWithDetailsPrintSchema),
        required=True,
        metadata=meta("Смены исполнителя в этот день", []),
    )


class WorkAggregatePrintSchema(PrintSchema):
    project_work = fields.Nested(
        ProjectWorkPrintSchema,
        required=True,
        metadata=meta("Позиция спецификации — ключ группировки", {}),
    )
    work = fields.Nested(
        WorkPrintSchema, required=True, metadata=meta("Работа каталога", {})
    )
    quantity = fields.Float(
        required=True, metadata=meta("Суммарное выполненное количество", 5.0)
    )
    summ = fields.Float(
        required=True,
        metadata=meta("Суммарная стоимость работы по спецификации", 751.25),
    )


class MaterialAggregatePrintSchema(PrintSchema):
    material = fields.Nested(
        MaterialPrintSchema,
        required=True,
        metadata=meta("Материал каталога — ключ группировки", {}),
    )
    quantity = fields.Float(
        required=True, metadata=meta("Суммарный расход материала", 6.0)
    )
    summ = fields.Float(
        required=True,
        metadata=meta("Сумма стоимости расходов по ценам их строк спецификации", 153.0),
    )


class ProjectAggregatePrintSchema(ProjectPrintSchema):
    works = fields.List(
        fields.Nested(WorkAggregatePrintSchema),
        required=True,
        metadata=meta("Работы проекта", []),
    )
    materials = fields.List(
        fields.Nested(MaterialAggregatePrintSchema),
        required=True,
        metadata=meta("Материалы проекта", []),
    )


class ObjectAggregatePrintSchema(ObjectPrintSchema):
    projects = fields.List(
        fields.Nested(ProjectAggregatePrintSchema),
        required=True,
        metadata=meta("Спецификации объекта с выполнением или расходом", []),
    )


class WorkTypesTemplateDataSchema(PrintSchema):
    works = fields.List(
        fields.Nested(WorkPrintSchema),
        required=True,
        metadata=meta("Каталог видов работ", []),
    )


class ShiftReportTemplateDataSchema(PrintSchema):
    shift_report = fields.Nested(
        ShiftReportFullPrintSchema,
        required=True,
        metadata=meta("Сменный отчёт с деталями и материалами", {}),
    )


class ShiftReportListTemplateDataSchema(PrintSchema):
    shift_reports = fields.List(
        fields.Nested(ShiftReportRegistryPrintSchema),
        required=True,
        metadata=meta("Реестр сменных отчётов", []),
    )


class PayrollTemplateDataSchema(PrintSchema):
    parameters = fields.Nested(
        PayrollParametersPrintSchema,
        required=True,
        metadata=meta("Параметры ведомости", {}),
    )
    user = fields.Nested(
        UserPrintSchema, required=True, metadata=meta("Исполнитель ведомости", {})
    )
    data = fields.List(
        fields.Nested(PayrollDayPrintSchema),
        required=True,
        metadata=meta("Все дни периода, включая пустые", []),
    )
    total_summ = fields.Float(
        required=True,
        metadata=meta(
            "Итог по расценкам спецификации; отсутствия не начисляются", 12345.67
        ),
    )


class ObjectReportTemplateDataSchema(PrintSchema):
    parameters = fields.Nested(
        ObjectReportParametersPrintSchema,
        required=True,
        metadata=meta("Параметры отчёта по объектам", {}),
    )
    objects = fields.List(
        fields.Nested(ObjectAggregatePrintSchema),
        required=True,
        metadata=meta("Объекты с проектами, работами и материалами", []),
    )


TEMPLATE_DATA_SCHEMAS: dict[TemplateTypes, type[Schema]] = {
    TemplateTypes.WORK_TYPES: WorkTypesTemplateDataSchema,
    TemplateTypes.SHIFT_REPORT: ShiftReportTemplateDataSchema,
    TemplateTypes.SHIFT_REPORT_LIST: ShiftReportListTemplateDataSchema,
    TemplateTypes.PAYROLL: PayrollTemplateDataSchema,
    TemplateTypes.OBJECT_REPORT: ObjectReportTemplateDataSchema,
}


def template_data_schema(template_type: TemplateTypes | str) -> Schema:
    """Instantiate the data contract without reading business data or S3."""
    return TEMPLATE_DATA_SCHEMAS[TemplateTypes(template_type)]()
