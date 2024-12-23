import logging
from flask_restx import Namespace, Resource
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.routes.models.work_category_models import (
    work_category_create_model,
    work_category_model,
    work_category_response,
    work_category_all_response,
    work_category_msg_model,
    work_category_filter_parser
)


logger = logging.getLogger('ok_service')

work_category_ns = Namespace(
    'work_category', description='Work category management operations')

work_category_ns.models[work_category_create_model.name] = work_category_create_model
work_category_ns.models[work_category_msg_model.name] = work_category_msg_model
work_category_ns.models[work_category_response.name] = work_category_response
work_category_ns.models[work_category_all_response.name] = work_category_all_response
work_category_ns.models[work_category_model.name] = work_category_model


@work_category_ns.route('/add')
class WorkCategoryAdd(Resource):
    @jwt_required()
    @work_category_ns.expect(work_category_create_model)
    @work_category_ns.marshal_with(work_category_msg_model)
    def post(self):
        current_user = get_jwt_identity()
        logger.info("Request to add new work category.",
                    extra={"login": current_user})

        name = request.json.get("name")

        if not name:
            logger.warning("Missing required parameter: name",
                           extra={"login": current_user})
            return {"msg": "Bad request, invalid data."}, 400

        try:
            from app.database.managers.works_managers import WorksCategoriesManager
            db = WorksCategoriesManager()
            logger.debug("Adding work category to the database...",
                         extra={"login": current_user})
            category_id = db.add(name=name)
            logger.info(f"""Successfully added new work category: {category_id}""",
                        extra={"login": current_user})
            return {"msg": "New work category added successfully"}, 200
        except Exception as e:
            logger.error(f"Error adding work category: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error in adding work category: {e}"}, 500


@work_category_ns.route('/<string:work_category_id>/view')
class WorkCategoryView(Resource):
    @jwt_required()
    @work_category_ns.marshal_with(work_category_response)
    def get(self, work_category_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to view work category: {work_category_id}",
                    extra={"login": current_user})

        from app.database.managers.works_managers import WorksCategoriesManager
        db = WorksCategoriesManager()

        try:
            work_category = db.get_by_id(work_category_id)
            if not work_category:
                return {"msg": "Work category not found"}, 404
            return {"msg": "Work category found successfully", "work_category": work_category}, 200
        except Exception as e:
            logger.error(f"Error viewing work category: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error viewing work category: {e}"}, 500


@work_category_ns.route('/<string:work_category_id>/delete/soft')
class WorkCategoryDeleteSoft(Resource):
    @jwt_required()
    @work_category_ns.marshal_with(work_category_msg_model)
    def patch(self, work_category_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to soft delete work category: {work_category_id}",
                    extra={"login": current_user})

        from app.database.managers.works_managers import WorksCategoriesManager
        db = WorksCategoriesManager()

        try:
            updated = db.update(record_id=work_category_id, deleted=True)
            if not updated:
                return {"msg": "Work category not found"}, 404
            return {"msg": f"Work category {work_category_id} soft deleted successfully"}, 200
        except Exception as e:
            logger.error(f"Error soft deleting work category: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error soft deleting work category: {e}"}, 500


@work_category_ns.route('/<string:work_category_id>/delete/hard')
class WorkCategoryDeleteHard(Resource):
    @jwt_required()
    @work_category_ns.marshal_with(work_category_msg_model)
    def delete(self, work_category_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to hard delete work category: {work_category_id}",
                    extra={"login": current_user})

        from app.database.managers.works_managers import WorksCategoriesManager
        db = WorksCategoriesManager()

        try:
            deleted = db.delete(record_id=work_category_id)
            if not deleted:
                return {"msg": "Work category not found"}, 404
            return {"msg": f"Work category {work_category_id} hard deleted successfully"}, 200
        except Exception as e:
            logger.error(f"Error hard deleting work category: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error hard deleting work category: {e}"}, 500


@work_category_ns.route('/<string:work_category_id>/edit')
class WorkCategoryEdit(Resource):
    @jwt_required()
    @work_category_ns.expect(work_category_create_model)
    @work_category_ns.marshal_with(work_category_msg_model)
    def patch(self, work_category_id):
        current_user = get_jwt_identity()
        logger.info(f"Request to edit work category: {work_category_id}",
                    extra={"login": current_user})

        name = request.json.get("name")

        if not name:
            logger.warning("Missing required parameter: name",
                           extra={"login": current_user})
            return {"msg": "Bad request, invalid data."}, 400

        from app.database.managers.works_managers import WorksCategoriesManager
        db = WorksCategoriesManager()

        try:
            updated = db.update(record_id=work_category_id, name=name)
            if not updated:
                return {"msg": "Work category not found"}, 404
            return {"msg": "Work category edited successfully"}, 200
        except Exception as e:
            logger.error(f"Error editing work category: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error editing work category: {e}"}, 500


@work_category_ns.route('/all')
class WorkCategoryAll(Resource):
    @jwt_required()
    @work_category_ns.expect(work_category_filter_parser)
    @work_category_ns.marshal_with(work_category_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info("Request to fetch all work categories.",
                    extra={"login": current_user})

        args = work_category_filter_parser.parse_args()
        offset = args.get('offset', 0)
        limit = args.get('limit', None)
        sort_by = args.get('sort_by')
        sort_order = args.get('sort_order', 'asc')
        filters = {
            'name': args.get('name')
        }

        from app.database.managers.works_managers import WorksCategoriesManager
        db = WorksCategoriesManager()

        try:
            work_categories = db.get_all_filtered(
                offset=offset, limit=limit, sort_by=sort_by, sort_order=sort_order, **filters)
            return {"msg": "Work categories found successfully", "work_categories": work_categories}, 200
        except Exception as e:
            logger.error(f"Error fetching work categories: {e}",
                         extra={"login": current_user})
            return {"msg": f"Error fetching work categories: {e}"}, 500
