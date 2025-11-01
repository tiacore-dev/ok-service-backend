import json
import logging
from uuid import UUID

from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.routes.models.object_models import (
    object_all_response,
    object_create_model,
    object_filter_parser,
    object_model,
    object_msg_model,
    object_response,
)
from app.schemas.object_schemas import (
    ObjectCreateSchema,
    ObjectEditSchema,
    ObjectFilterSchema,
)

logger = logging.getLogger("ok_service")

object_ns = Namespace("objects", description="Objects management operations")

# Инициализация моделей
object_ns.models[object_create_model.name] = object_create_model
object_ns.models[object_msg_model.name] = object_msg_model
object_ns.models[object_response.name] = object_response
object_ns.models[object_all_response.name] = object_all_response
object_ns.models[object_model.name] = object_model


@object_ns.route("/add")
class ObjectAdd(Resource):
    @jwt_required()
    @object_ns.expect(object_create_model)
    @object_ns.marshal_with(object_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.debug(f"Decoded JWT Identity: {current_user}")
        if current_user["role"] != "admin":
            logger.warning(
                "Несанкционированный запрос на добавление нового объекта.",
                extra={"login": current_user},
            )
            return {"msg": "Forbidden"}, 403
        logger.info("Request to add new object", extra={"login": current_user})
        from app.database.managers.objects_managers import ObjectStatusesManager

        db_s = ObjectStatusesManager()
        data = request.json
        object_status_id = data.get("status")  # type: ignore
        if not db_s.exists_by_id(record_id=object_status_id):
            logger.warning(
                f"Invalid object status ID: {object_status_id}",
                extra={"login": current_user},
            )
            return {"msg": "Invalid object status"}, 400
        schema = ObjectCreateSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            return {"error": err.messages}, 400
        try:
            from app.database.managers.objects_managers import ObjectsManager

            db = ObjectsManager()
            city_id = data.pop("city")  # type: ignore
            new_object = db.add(  # type: ignore
                created_by=current_user["user_id"],
                city_id=city_id,
                **data,  # type: ignore
            )
            logger.info(
                f"New object added: {new_object['object_id']}",
                extra={"login": current_user},
            )
            return {
                "msg": "New object added successfully",
                "object_id": new_object["object_id"],
            }, 200
        except Exception as e:
            logger.error(f"Error adding object: {e}", extra={"login": current_user})
            return {"msg": f"Error adding object: {e}"}, 500


@object_ns.route("/<string:object_id>/view")
class ObjectView(Resource):
    @jwt_required()
    @object_ns.marshal_with(object_response)
    def get(self, object_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to view object: {object_id}", extra={"login": current_user}
        )
        try:
            try:
                object_id = UUID(object_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.objects_managers import ObjectsManager

            db = ObjectsManager()
            obj = db.get_by_id(object_id)
            if not obj:
                logger.warning(
                    f"Object {object_id} not found", extra={"login": current_user}
                )
                return {"msg": "Object not found"}, 404
            if current_user["role"] == "user" and obj["status"] != "active":
                logger.warning(
                    f"Access denied for user to object {object_id} with status '{
                        obj['status']
                    }'",
                    extra={"login": current_user},
                )
                return {"msg": "Forbidden"}, 403
            return {"msg": "Object found successfully", "object": obj}, 200
        except Exception as e:
            logger.error(f"Error viewing object: {e}", extra={"login": current_user})
            return {"msg": f"Error viewing object: {e}"}, 500


@object_ns.route("/<string:object_id>/delete/soft")
class ObjectSoftDelete(Resource):
    @jwt_required()
    @object_ns.marshal_with(object_msg_model)
    def patch(self, object_id):
        current_user = json.loads(get_jwt_identity())
        logger.debug(f"Decoded JWT Identity: {current_user}")
        if current_user["role"] != "admin":
            logger.warning(
                "Несанкционированный запрос на мягкое удаление объекта.",
                extra={"login": current_user},
            )
            return {"msg": "Forbidden"}, 403
        logger.info(
            f"Request to soft delete object: {object_id}", extra={"login": current_user}
        )
        try:
            try:
                object_id = UUID(object_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.objects_managers import ObjectsManager

            db = ObjectsManager()
            updated = db.update(record_id=object_id, deleted=True)
            if not updated:
                logger.warning(
                    f"Object {object_id} not found for soft delete",
                    extra={"login": current_user},
                )
                return {"msg": "Object not found"}, 404
            return {
                "msg": f"Object {object_id} soft deleted successfully",
                "object_id": object_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error soft deleting object: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error soft deleting object: {e}"}, 500


@object_ns.route("/<string:object_id>/delete/hard")
class ObjectHardDelete(Resource):
    @jwt_required()
    @object_ns.marshal_with(object_msg_model)
    def delete(self, object_id):
        current_user = json.loads(get_jwt_identity())
        logger.debug(f"Decoded JWT Identity: {current_user}")
        if current_user["role"] != "admin":
            logger.warning(
                "Несанкционированный запрос на удаление (hard) объекта.",
                extra={"login": current_user},
            )
            return {"msg": "Forbidden"}, 403
        logger.info(
            f"Request to hard delete object: {object_id}", extra={"login": current_user}
        )
        try:
            try:
                object_id = UUID(object_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.objects_managers import ObjectsManager

            db = ObjectsManager()
            deleted = db.delete(record_id=object_id)
            if not deleted:
                logger.warning(
                    f"Object {object_id} not found for hard delete",
                    extra={"login": current_user},
                )
                return {"msg": "Object not found"}, 404
            return {
                "msg": f"Object {object_id} hard deleted successfully",
                "object_id": object_id,
            }, 200
        except IntegrityError:
            logger.warning(
                f"Cannot hard delete object {object_id}: dependent data exists",
                extra={"login": current_user},
            )
            abort(409, description="Cannot delete object: dependent data exists.")
        except Exception as e:
            logger.error(
                f"Error hard deleting object: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error hard deleting object: {e}"}, 500


@object_ns.route("/<string:object_id>/edit")
class ObjectEdit(Resource):
    @jwt_required()
    @object_ns.expect(object_create_model)
    @object_ns.marshal_with(object_msg_model)
    def patch(self, object_id):
        current_user = json.loads(get_jwt_identity())
        logger.debug(f"Decoded JWT Identity: {current_user}")
        if current_user["role"] != "admin":
            logger.warning(
                "Несанкционированный запрос на изменение объекта.",
                extra={"login": current_user},
            )
            return {"msg": "Forbidden"}, 403
        logger.info(
            f"Request to edit object: {object_id}", extra={"login": current_user}
        )

        schema = ObjectEditSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error: {err.messages}", extra={"login": current_user}
            )
            return {"error": err.messages}, 400
        if "city" in data:  # type: ignore
            city_value = data.pop("city")  # type: ignore
            if city_value is not None:
                data["city_id"] = city_value  # type: ignore
        try:
            try:
                object_id = UUID(object_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.objects_managers import ObjectsManager

            db = ObjectsManager()
            updated = db.update(record_id=object_id, **data)  # type: ignore
            if not updated:
                logger.warning(
                    f"Object {object_id} not found for editing",
                    extra={"login": current_user},
                )
                return {"msg": "Object not found"}, 404
            return {"msg": "Object edited successfully", "object_id": object_id}, 200
        except Exception as e:
            logger.error(f"Error editing object: {e}", extra={"login": current_user})
            return {"msg": f"Error editing object: {e}"}, 500


@object_ns.route("/all")
class ObjectAll(Resource):
    @jwt_required()
    @object_ns.expect(object_filter_parser)
    @object_ns.marshal_with(object_all_response)
    def get(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to fetch all objects", extra={"login": current_user})

        schema = ObjectFilterSchema()
        try:
            data = schema.load(request.args)
        except ValidationError as err:
            logger.error(
                f"Validation error: {err.messages}", extra={"login": current_user}
            )
            return {"error": err.messages}, 400

        offset = data.get("offset", 0)  # type: ignore
        limit = data.get("limit", None)  # type: ignore
        sort_by = data.get("sort_by")  # type: ignore
        sort_order = data.get("sort_order", "desc")  # type: ignore
        filters = {
            "name": data.get("name"),  # type: ignore
            "deleted": data.get("deleted"),  # type: ignore
            "address": data.get("address"),  # type: ignore
            "status": data.get("status"),  # type: ignore
            "created_by": data.get("created_by"),  # type: ignore
            "created_at": data.get("created_at"),  # type: ignore
            "city_id": data.get("city"),  # type: ignore
            "lng": data.get("lng"),  # type: ignore
            "ltd": data.get("ltd"),  # type: ignore
        }
        if current_user["role"] == "user":
            filters["status"] = "active"

        logger.debug(
            f"Fetching objects with filters: {filters}, offset={offset}, limit={limit}",
            extra={"login": current_user},
        )

        try:
            from app.database.managers.objects_managers import ObjectsManager

            db = ObjectsManager()
            objects = db.get_all_filtered(
                offset=offset,
                limit=limit,
                sort_by=sort_by,  # type: ignore
                sort_order=sort_order,
                **filters,
            )
            logger.info(
                f"Successfully fetched {len(objects)} objects",
                extra={"login": current_user},
            )
            return {"msg": "Objects found successfully", "objects": objects}, 200
        except Exception as e:
            logger.error(f"Error fetching objects: {e}", extra={"login": current_user})
            return {"msg": f"Error fetching objects: {e}"}, 500
