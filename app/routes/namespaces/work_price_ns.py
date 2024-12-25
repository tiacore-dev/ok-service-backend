import logging
from uuid import UUID
from flask import request
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.routes.models.work_price_models import (
    work_price_create_model,
    work_price_msg_model,
    work_price_response,
    work_price_all_response,
    work_price_filter_parser,
    work_price_model
)

logger = logging.getLogger('ok_service')

work_price_ns = Namespace(
    'work_prices', description='Work Prices management operations')

# Инициализация моделей
work_price_ns.models[work_price_create_model.name] = work_price_create_model
work_price_ns.models[work_price_msg_model.name] = work_price_msg_model
work_price_ns.models[work_price_response.name] = work_price_response
work_price_ns.models[work_price_all_response.name] = work_price_all_response
work_price_ns.models[work_price_model.name] = work_price_model


@work_price_ns.route('/add')
class WorkPriceAdd(Resource):
    @jwt_required()
    @work_price_ns.expect(work_price_create_model)
    @work_price_ns.marshal_with(work_price_msg_model)
    def post(self):
        current_user = get_jwt_identity()
        logger.info("Request to add new work price",
                    extra={"login": current_user})

        data = request.json
        try:
            from app.database.managers.works_managers import WorkPricesManager
            db = WorkPricesManager()

            # Добавление цены работы
            new_work_price = db.add(**data)
            logger.info(f"New work price added: {new_work_price['work_price_id']}",
                        extra={"login": current_user})
            return {"msg": "New work price added successfully"}, 200
        except Exception as e:
            logger.error(f"Error adding work price: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error adding work price: {e}"}, 500


@work_price_ns.route('/<string:work_price_id>/view')
class WorkPriceView(Resource):
    @jwt_required()
    @work_price_ns.marshal_with(work_price_response)
    def get(self, work_price_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to view work price: {work_price_id}",
                    extra={"login": current_user})
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
                return {"msg": "Work price not found"}, 404
            return {"msg": "Work price found successfully", "work_price": work_price}, 200
        except Exception as e:
            logger.error(f"Error viewing work price: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error viewing work price: {e}"}, 500


@work_price_ns.route('/<string:work_price_id>/delete/soft')
class WorkPriceSoftDelete(Resource):
    @jwt_required()
    @work_price_ns.marshal_with(work_price_msg_model)
    def patch(self, work_price_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to soft delete work price: {work_price_id}",
                    extra={"login": current_user})
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
                return {"msg": "Work price not found"}, 404
            return {"msg": f"Work price {work_price_id} soft deleted successfully"}, 200
        except Exception as e:
            logger.error(f"Error soft deleting work price: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error soft deleting work price: {e}"}, 500


@work_price_ns.route('/<string:work_price_id>/delete/hard')
class WorkPriceHardDelete(Resource):
    @jwt_required()
    @work_price_ns.marshal_with(work_price_msg_model)
    def delete(self, work_price_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to hard delete work price: {work_price_id}",
                    extra={"login": current_user})
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
                return {"msg": "Work price not found"}, 404
            return {"msg": f"Work price {work_price_id} hard deleted successfully"}, 200
        except Exception as e:
            logger.error(f"Error hard deleting work price: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error hard deleting work price: {e}"}, 500


@work_price_ns.route('/<string:work_price_id>/edit')
class WorkPriceEdit(Resource):
    @jwt_required()
    @work_price_ns.expect(work_price_create_model)
    @work_price_ns.marshal_with(work_price_msg_model)
    def patch(self, work_price_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to edit work price: {work_price_id}",
                    extra={"login": current_user})

        data = request.json
        try:
            try:
                # Конвертируем строку в UUID
                work_price_id = UUID(work_price_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.works_managers import WorkPricesManager
            db = WorkPricesManager()
            updated = db.update(record_id=work_price_id, **data)
            if not updated:
                return {"msg": "Work price not found"}, 404
            return {"msg": "Work price edited successfully"}, 200
        except Exception as e:
            logger.error(f"Error editing work price: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error editing work price: {e}"}, 500


@work_price_ns.route('/all')
class WorkPriceAll(Resource):
    @jwt_required()
    @work_price_ns.expect(work_price_filter_parser)
    @work_price_ns.marshal_with(work_price_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info("Request to fetch all work prices",
                    extra={"login": current_user})

        args = work_price_filter_parser.parse_args()
        offset = args.get('offset', 0)
        limit = args.get('limit', None)
        sort_by = args.get('sort_by')
        sort_order = args.get('sort_order', 'asc')
        filters = {
            'name': args.get('name'),
            'deleted': args.get('deleted'),
        }

        logger.debug(f"Fetching work prices with filters: {filters}, offset={offset}, limit={limit}, sort_by={sort_by}, sort_order={sort_order}",
                     extra={"login": current_user})

        try:
            from app.database.managers.works_managers import WorkPricesManager
            db = WorkPricesManager()
            work_prices = db.get_all_filtered(
                offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order, **filters)
            logger.info(f"Successfully fetched {len(work_prices)} work prices",
                        extra={"login": current_user})
            return {"msg": "Work prices found successfully", "work_prices": work_prices}, 200
        except Exception as e:
            logger.error(f"Error fetching work prices: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error fetching work prices: {e}"}, 500
