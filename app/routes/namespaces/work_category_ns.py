import json
import logging

from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.decorators import admin_required
from app.routes.models.work_category_models import (
    work_category_all_response,
    work_category_create_model,
    work_category_filter_parser,
    work_category_model,
    work_category_msg_model,
    work_category_response,
)
from app.schemas.work_category_schemas import (
    WorkCategoryCreateSchema,
    WorkCategoryEditSchema,
    WorkCategoryFilterSchema,
)

logger = logging.getLogger("ok_service")

work_category_ns = Namespace(
    "work_categories", description="Work category management operations"
)

work_category_ns.models[work_category_create_model.name] = work_category_create_model
work_category_ns.models[work_category_msg_model.name] = work_category_msg_model
work_category_ns.models[work_category_response.name] = work_category_response
work_category_ns.models[work_category_all_response.name] = work_category_all_response
work_category_ns.models[work_category_model.name] = work_category_model


@work_category_ns.route("/add")
class WorkCategoryAdd(Resource):
    @jwt_required()
    @admin_required
    @work_category_ns.expect(work_category_create_model)
    @work_category_ns.marshal_with(work_category_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to add new work category.", extra={"login": current_user})
        schema = WorkCategoryCreateSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while adding work category: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        name = data.get("name")  # type: ignore

        if not name:
            logger.warning(
                "Missing required field 'name' in add request.",
                extra={"login": current_user},
            )
            return {"msg": "Bad request, invalid data."}, 400

        try:
            from app.database.managers.works_managers import WorkCategoriesManager

            db = WorkCategoriesManager()
            logger.debug(
                "Adding work category to the database...", extra={"login": current_user}
            )
            new_category = db.add(created_by=current_user["user_id"], name=name)
            logger.info(
                f"""Successfully added new work category: {
                    new_category["work_category_id"]
                }""",
                extra={"login": current_user},
            )
            return {
                "msg": "New work category added successfully",
                "work_category_id": new_category["work_category_id"],
            }, 200
        except Exception as e:
            logger.error(
                f"Error adding work category: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error in adding work category: {e}"}, 500


@work_category_ns.route("/<string:work_category_id>/view")
class WorkCategoryView(Resource):
    @jwt_required()
    @work_category_ns.marshal_with(work_category_response)
    def get(self, work_category_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to view work category: {work_category_id}",
            extra={"login": current_user},
        )

        from app.database.managers.works_managers import WorkCategoriesManager

        db = WorkCategoriesManager()

        try:
            work_category = db.get_by_id(work_category_id)
            if not work_category:
                logger.warning(
                    f"Work category not found: {work_category_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Work category not found"}, 404
            return {
                "msg": "Work category found successfully",
                "work_category": work_category,
            }, 200
        except Exception as e:
            logger.error(
                f"Error viewing work category: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error viewing work category: {e}"}, 500


@work_category_ns.route("/<string:work_category_id>/delete/soft")
class WorkCategoryDeleteSoft(Resource):
    @jwt_required()
    @admin_required
    @work_category_ns.marshal_with(work_category_msg_model)
    def patch(self, work_category_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to soft delete work category: {work_category_id}",
            extra={"login": current_user},
        )

        from app.database.managers.works_managers import WorkCategoriesManager

        db = WorkCategoriesManager()

        try:
            updated = db.update(record_id=work_category_id, deleted=True)
            if not updated:
                logger.warning(
                    f"Work category not found for soft delete: {work_category_id}",
                    extra={"login": current_user},
                )

                return {"msg": "Work category not found"}, 404
            return {
                "msg": f"Work category {work_category_id} soft deleted successfully",
                "work_category_id": work_category_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error soft deleting work category: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error soft deleting work category: {e}"}, 500


@work_category_ns.route("/<string:work_category_id>/delete/hard")
class WorkCategoryDeleteHard(Resource):
    @jwt_required()
    @admin_required
    @work_category_ns.marshal_with(work_category_msg_model)
    def delete(self, work_category_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to hard delete work category: {work_category_id}",
            extra={"login": current_user},
        )

        from app.database.managers.works_managers import WorkCategoriesManager

        db = WorkCategoriesManager()

        try:
            deleted = db.delete(record_id=work_category_id)
            if not deleted:
                logger.warning(
                    f"Work category not found for hard delete: {work_category_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Work category not found"}, 404
            return {
                "msg": f"Work category {work_category_id} hard deleted successfully",
                "work_category_id": work_category_id,
            }, 200
        except IntegrityError:
            logger.warning(
                f"Cannot delete work category due to existing dependencies: {
                    work_category_id
                }",
                extra={"login": current_user},
            )
            abort(
                409, description="Cannot delete work category: dependent data exists."
            )
        except Exception as e:
            logger.error(
                f"Error hard deleting work category: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error hard deleting work category: {e}"}, 500


@work_category_ns.route("/<string:work_category_id>/edit")
class WorkCategoryEdit(Resource):
    @jwt_required()
    @admin_required
    @work_category_ns.expect(work_category_create_model)
    @work_category_ns.marshal_with(work_category_msg_model)
    def patch(self, work_category_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to edit work category: {work_category_id}",
            extra={"login": current_user},
        )
        schema = WorkCategoryEditSchema()
        try:
            # Валидация входных данных
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while editing work category: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        name = data.get("name")  # type: ignore

        if not name:
            logger.warning(
                "Missing required field 'name' in edit request.",
                extra={"login": current_user},
            )
            return {"msg": "Bad request, invalid data."}, 400

        from app.database.managers.works_managers import WorkCategoriesManager

        db = WorkCategoriesManager()

        try:
            updated = db.update(record_id=work_category_id, name=name)
            if not updated:
                logger.warning(
                    f"Work category not found for edit: {work_category_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Work category not found"}, 404
            return {
                "msg": "Work category edited successfully",
                "work_category_id": work_category_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error editing work category: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error editing work category: {e}"}, 500


@work_category_ns.route("/all")
class WorkCategoryAll(Resource):
    @jwt_required()
    @work_category_ns.expect(work_category_filter_parser)
    @work_category_ns.marshal_with(work_category_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info(
            "Request to fetch all work categories.", extra={"login": current_user}
        )

        # Валидация query-параметров через Marshmallow
        schema = WorkCategoryFilterSchema()
        try:
            args = schema.load(request.args)  # Валидируем query-параметры
        except ValidationError as err:
            logger.error(
                f"Validation error while filtering work categories: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit", 10)  # type: ignore
        sort_by = args.get("sort_by")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore
        filters = {
            "name": args.get("name"),  # type: ignore
            "created_by": args.get("created_by"),  # type: ignore
            "created_at": args.get("created_at"),  # type: ignore
        }

        from app.database.managers.works_managers import WorkCategoriesManager

        db = WorkCategoriesManager()

        try:
            work_categories = db.get_all_filtered(
                offset=offset,
                limit=limit,
                sort_by=sort_by,  # type: ignore
                sort_order=sort_order,
                **filters,
            )
            logger.info(
                f"Successfully fetched {len(work_categories)} work categories",
                extra={"login": current_user},
            )
            return {
                "msg": "Work categories found successfully",
                "work_categories": work_categories,
            }, 200
        except Exception as e:
            logger.error(
                f"Error fetching work categories: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error fetching work categories: {e}"}, 500
