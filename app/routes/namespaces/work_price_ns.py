import json
import logging
from uuid import UUID

from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.decorators import admin_required
from app.routes.models.work_price_models import (
    work_price_all_response,
    work_price_create_model,
    work_price_filter_parser,
    work_price_model,
    work_price_msg_model,
    work_price_response,
)
from app.schemas.work_price_schemas import (
    WorkPriceCreateSchema,
    WorkPriceEditSchema,
    WorkPriceFilterSchema,
)

logger = logging.getLogger("ok_service")

work_price_ns = Namespace(
    "work_prices", description="Work Prices management operations"
)

# Инициализация моделей
work_price_ns.models[work_price_create_model.name] = work_price_create_model
work_price_ns.models[work_price_msg_model.name] = work_price_msg_model
work_price_ns.models[work_price_response.name] = work_price_response
work_price_ns.models[work_price_all_response.name] = work_price_all_response
work_price_ns.models[work_price_model.name] = work_price_model


@work_price_ns.route("/add")
class WorkPriceAdd(Resource):
    @jwt_required()
    @admin_required
    @work_price_ns.expect(work_price_create_model)
    @work_price_ns.marshal_with(work_price_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        if current_user["role"] != "admin":
            logger.warning(
                "Несанкционированный запрос на добавление нового объекта.",
                extra={"login": current_user.get("login")},
            )
            return {"msg": "Forbidden"}, 403
        logger.info("Request to add new work price", extra={"login": current_user})

        schema = WorkPriceCreateSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while adding work price: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        try:
            from app.database.managers.works_managers import WorkPricesManager

            db = WorkPricesManager()

            # Добавление цены работы
            new_work_price = db.add(created_by=current_user["user_id"], **data)  # type: ignore
            logger.info(
                f"New work price added: {new_work_price['work_price_id']}",
                extra={"login": current_user},
            )
            return {
                "msg": "New work price added successfully",
                "work_price_id": new_work_price["work_price_id"],
            }, 200
        except Exception as e:
            logger.error(f"Error adding work price: {e}", extra={"login": current_user})
            return {"msg": f"Error adding work price: {e}"}, 500


@work_price_ns.route("/<string:work_price_id>/view")
class WorkPriceView(Resource):
    @jwt_required()
    @work_price_ns.marshal_with(work_price_response)
    def get(self, work_price_id):
        current_user = get_jwt_identity()
        logger.info(
            f"Request to view work price: {work_price_id}",
            extra={"login": current_user},
        )
        try:
            try:
                # Конвертируем строку в UUID
                work_price_id = UUID(work_price_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.works_managers import WorkPricesManager

            db = WorkPricesManager()
            work_price = db.get_by_id(work_price_id)
            if not work_price:
                logger.warning(
                    f"Work price not found: {work_price_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Work price not found"}, 404
            return {
                "msg": "Work price found successfully",
                "work_price": work_price,
            }, 200
        except Exception as e:
            logger.error(
                f"Error viewing work price: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error viewing work price: {e}"}, 500


@work_price_ns.route("/<string:work_price_id>/delete/soft")
class WorkPriceSoftDelete(Resource):
    @jwt_required()
    @admin_required
    @work_price_ns.marshal_with(work_price_msg_model)
    def patch(self, work_price_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to soft delete work price: {work_price_id}",
            extra={"login": current_user},
        )
        try:
            try:
                # Конвертируем строку в UUID
                work_price_id = UUID(work_price_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.works_managers import WorkPricesManager

            db = WorkPricesManager()
            updated = db.update(record_id=work_price_id, deleted=True)
            if not updated:
                logger.warning(
                    f"Work price not found for soft delete: {work_price_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Work price not found"}, 404
            return {
                "msg": f"Work price {work_price_id} soft deleted successfully",
                "work_price_id": work_price_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error soft deleting work price: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error soft deleting work price: {e}"}, 500


@work_price_ns.route("/<string:work_price_id>/delete/hard")
class WorkPriceHardDelete(Resource):
    @jwt_required()
    @admin_required
    @work_price_ns.marshal_with(work_price_msg_model)
    def delete(self, work_price_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to hard delete work price: {work_price_id}",
            extra={"login": current_user},
        )
        try:
            try:
                # Конвертируем строку в UUID
                work_price_id = UUID(work_price_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.works_managers import WorkPricesManager

            db = WorkPricesManager()
            deleted = db.delete(record_id=work_price_id)
            if not deleted:
                logger.warning(
                    f"Work price not found for hard delete: {work_price_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Work price not found"}, 404
            return {
                "msg": f"Work price {work_price_id} hard deleted successfully",
                "work_price_id": work_price_id,
            }, 200
        except IntegrityError:
            logger.warning(
                f"Cannot hard delete work price {work_price_id} due to related data",
                extra={"login": current_user},
            )
            abort(409, description="Cannot delete work price: dependent data exists.")
        except Exception as e:
            logger.error(
                f"Error hard deleting work price: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error hard deleting work price: {e}"}, 500


@work_price_ns.route("/<string:work_price_id>/edit")
class WorkPriceEdit(Resource):
    @jwt_required()
    @admin_required
    @work_price_ns.expect(work_price_create_model)
    @work_price_ns.marshal_with(work_price_msg_model)
    def patch(self, work_price_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to edit work price: {work_price_id}",
            extra={"login": current_user},
        )

        schema = WorkPriceEditSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while editing work price: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        try:
            try:
                # Конвертируем строку в UUID
                work_price_id = UUID(work_price_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.works_managers import WorkPricesManager

            db = WorkPricesManager()
            updated = db.update(record_id=work_price_id, **data)  # type: ignore
            if not updated:
                logger.warning(
                    f"Work price not found for edit: {work_price_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Work price not found"}, 404
            return {
                "msg": "Work price edited successfully",
                "work_price_id": work_price_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error editing work price: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error editing work price: {e}"}, 500


@work_price_ns.route("/all")
class WorkPriceAll(Resource):
    @jwt_required()
    @work_price_ns.expect(work_price_filter_parser)
    @work_price_ns.marshal_with(work_price_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info("Request to fetch all work prices", extra={"login": current_user})

        # Валидация query-параметров через Marshmallow
        schema = WorkPriceFilterSchema()
        try:
            args = schema.load(request.args)  # Валидируем query-параметры
        except ValidationError as err:
            logger.error(
                f"Validation error while filtering work prices: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit", None)  # type: ignore
        sort_by = args.get("sort_by")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore
        filters = {
            # name в модели WorkPrices отсутствует, возможно, ошибка
            "work": args.get("work"),  # type: ignore
            "deleted": args.get("deleted"),  # type: ignore
            "category": args.get("category"),  # type: ignore
            "price": args.get("price"),  # type: ignore
            "created_by": args.get("created_by"),  # type: ignore
            "created_at": args.get("created_at"),  # type: ignore
        }

        logger.debug(
            f"Fetching work prices with filters: {filters}, offset={offset}, limit={
                limit
            }, sort_by={sort_by}, sort_order={sort_order}",
            extra={"login": current_user},
        )

        try:
            from app.database.managers.works_managers import WorkPricesManager

            db = WorkPricesManager()
            work_prices = db.get_all_filtered(
                offset=offset,
                limit=limit,
                sort_by=sort_by,  # type: ignore
                sort_order=sort_order,
                **filters,
            )
            logger.info(
                f"Successfully fetched {len(work_prices)} work prices",
                extra={"login": current_user},
            )
            return {
                "msg": "Work prices found successfully",
                "work_prices": work_prices,
            }, 200
        except Exception as e:
            logger.error(
                f"Error fetching work prices: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error fetching work prices: {e}"}, 500
