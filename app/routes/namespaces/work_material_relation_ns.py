import json
import logging
from uuid import UUID

from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.decorators import admin_required
from app.routes.models.work_material_relation_models import (
    work_material_relation_all_response,
    work_material_relation_create_model,
    work_material_relation_filter_parser,
    work_material_relation_model,
    work_material_relation_msg_model,
    work_material_relation_response,
)
from app.schemas.work_material_relation_schemas import (
    WorkMaterialRelationCreateSchema,
    WorkMaterialRelationEditSchema,
    WorkMaterialRelationFilterSchema,
)

logger = logging.getLogger("ok_service")

work_material_relation_ns = Namespace(
    "work_material_relations",
    description="Work material relations management operations",
)

work_material_relation_ns.models[work_material_relation_create_model.name] = (
    work_material_relation_create_model
)
work_material_relation_ns.models[work_material_relation_msg_model.name] = (
    work_material_relation_msg_model
)
work_material_relation_ns.models[work_material_relation_response.name] = (
    work_material_relation_response
)
work_material_relation_ns.models[work_material_relation_all_response.name] = (
    work_material_relation_all_response
)
work_material_relation_ns.models[work_material_relation_model.name] = (
    work_material_relation_model
)


@work_material_relation_ns.route("/add")
class WorkMaterialRelationAdd(Resource):
    @jwt_required()
    @admin_required
    @work_material_relation_ns.expect(work_material_relation_create_model)
    @work_material_relation_ns.marshal_with(work_material_relation_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            "Request to add new work material relation",
            extra={"login": current_user},
        )

        schema = WorkMaterialRelationCreateSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while adding work material relation: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        try:
            from app.database.managers.materials_manager import (
                WorkMaterialRelationsManager,
            )

            db = WorkMaterialRelationsManager()
            new_relation = db.add(created_by=current_user["user_id"], **data)  # type: ignore
            logger.info(
                f"New work material relation added: {
                    new_relation['work_material_relation_id']
                }",
                extra={"login": current_user},
            )
            return {
                "msg": "Work material relation added successfully",
                "work_material_relation_id": new_relation["work_material_relation_id"],
            }, 200
        except Exception as e:
            logger.error(
                f"Error adding work material relation: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error adding work material relation: {e}"}, 500


@work_material_relation_ns.route("/<string:relation_id>/view")
class WorkMaterialRelationView(Resource):
    @jwt_required()
    @work_material_relation_ns.marshal_with(work_material_relation_response)
    def get(self, relation_id):
        current_user = get_jwt_identity()
        logger.info(
            f"Request to view work material relation: {relation_id}",
            extra={"login": current_user},
        )
        try:
            try:
                relation_id = UUID(relation_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.materials_manager import (
                WorkMaterialRelationsManager,
            )

            db = WorkMaterialRelationsManager()
            relation = db.get_by_id(relation_id)
            if not relation:
                logger.warning(
                    f"Work material relation not found: {relation_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Work material relation not found"}, 404
            return {
                "msg": "Work material relation found successfully",
                "work_material_relation": relation,
            }, 200
        except Exception as e:
            logger.error(
                f"Error viewing work material relation: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error viewing work material relation: {e}"}, 500


@work_material_relation_ns.route("/<string:relation_id>/delete/hard")
class WorkMaterialRelationHardDelete(Resource):
    @jwt_required()
    @admin_required
    @work_material_relation_ns.marshal_with(work_material_relation_msg_model)
    def delete(self, relation_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to hard delete work material relation: {relation_id}",
            extra={"login": current_user},
        )
        try:
            try:
                relation_id = UUID(relation_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.materials_manager import (
                WorkMaterialRelationsManager,
            )

            db = WorkMaterialRelationsManager()
            deleted = db.delete(record_id=relation_id)
            if not deleted:
                logger.warning(
                    f"Work material relation not found for hard delete: {relation_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Work material relation not found"}, 404
            return {
                "msg": f"Work material relation {
                    relation_id
                } hard deleted successfully",
                "work_material_relation_id": relation_id,
            }, 200
        except IntegrityError:
            logger.warning(
                f"Cannot hard delete work material relation {
                    relation_id
                } due to related data",
                extra={"login": current_user},
            )
            abort(
                409,
                description="Cannot delete work material relation: "
                "dependent data exists.",
            )
        except Exception as e:
            logger.error(
                f"Error hard deleting work material relation: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error hard deleting work material relation: {e}"}, 500


@work_material_relation_ns.route("/<string:relation_id>/edit")
class WorkMaterialRelationEdit(Resource):
    @jwt_required()
    @admin_required
    @work_material_relation_ns.expect(work_material_relation_create_model)
    @work_material_relation_ns.marshal_with(work_material_relation_msg_model)
    def patch(self, relation_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to edit work material relation: {relation_id}",
            extra={"login": current_user},
        )

        schema = WorkMaterialRelationEditSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while editing work material relation: {
                    err.messages
                }",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        try:
            try:
                relation_id = UUID(relation_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.materials_manager import (
                WorkMaterialRelationsManager,
            )

            db = WorkMaterialRelationsManager()
            updated = db.update(record_id=relation_id, **data)  # type: ignore
            if not updated:
                logger.warning(
                    f"Work material relation not found for edit: {relation_id}",
                    extra={"login": current_user},
                )
                return {"msg": "Work material relation not found"}, 404
            return {
                "msg": "Work material relation edited successfully",
                "work_material_relation_id": relation_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error editing work material relation: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error editing work material relation: {e}"}, 500


@work_material_relation_ns.route("/all")
class WorkMaterialRelationAll(Resource):
    @jwt_required()
    @work_material_relation_ns.expect(work_material_relation_filter_parser)
    @work_material_relation_ns.marshal_with(work_material_relation_all_response)
    def get(self):
        current_user = get_jwt_identity()
        logger.info(
            "Request to fetch all work material relations",
            extra={"login": current_user},
        )

        schema = WorkMaterialRelationFilterSchema()
        try:
            args = schema.load(request.args)
        except ValidationError as err:
            logger.error(
                f"Validation error while filtering work material relations: {
                    err.messages
                }",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400
        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit", None)  # type: ignore
        sort_by = args.get("sort_by")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore
        filters = {
            "work": args.get("work"),  # type: ignore
            "material": args.get("material"),  # type: ignore
            "created_by": args.get("created_by"),  # type: ignore
            "created_at": args.get("created_at"),  # type: ignore
        }

        logger.debug(
            f"Fetching work material relations with filters: {filters}, offset={
                offset
            }, "
            f"limit={limit}, sort_by={sort_by}, sort_order={sort_order}",
            extra={"login": current_user},
        )

        try:
            from app.database.managers.materials_manager import (
                WorkMaterialRelationsManager,
            )

            db = WorkMaterialRelationsManager()
            relations = db.get_all_filtered(
                offset=offset,
                limit=limit,
                sort_by=sort_by,  # type: ignore
                sort_order=sort_order,
                **filters,
            )
            logger.info(
                f"Successfully fetched {len(relations)} work material relations",
                extra={"login": current_user},
            )
            return {
                "msg": "Work material relations found successfully",
                "work_material_relations": relations,
            }, 200
        except Exception as e:
            logger.error(
                f"Error fetching work material relations: {e}",
                extra={"login": current_user},
            )
            return {"msg": f"Error fetching work material relations: {e}"}, 500
