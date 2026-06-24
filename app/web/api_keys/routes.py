import json
import logging
from uuid import UUID

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.decorators import admin_required
from app.schemas.api_key_schemas import ApiKeyFilterSchema, ApiKeyGenerateSchema
from app.schemas.key_permission_type_relation_schemas import (
    KeyPermissionTypeRelationBulkCreateSchema,
    KeyPermissionTypeRelationBulkDeleteSchema,
    KeyPermissionTypeRelationCreateSchema,
    PermissionTypeFilterSchema,
)

from .models import (
    api_key_all_response,
    api_key_filter_parser,
    api_key_generate_model,
    api_key_generate_response,
    api_key_model,
    api_key_msg_model,
    api_key_response,
    key_permission_relation_all_response,
    key_permission_relation_bulk_create_model,
    key_permission_relation_bulk_delete_model,
    key_permission_relation_bulk_delete_response,
    key_permission_relation_bulk_response,
    key_permission_relation_create_model,
    key_permission_relation_filter_parser,
    key_permission_relation_model,
    key_permission_relation_msg_model,
    key_permission_relation_response,
    permission_type_all_response,
    permission_type_filter_parser,
    permission_type_model,
)

logger = logging.getLogger("ok_service")

api_key_ns = Namespace("api-key", description="API keys management operations")

api_key_ns.models[api_key_generate_model.name] = api_key_generate_model
api_key_ns.models[api_key_generate_response.name] = api_key_generate_response
api_key_ns.models[api_key_msg_model.name] = api_key_msg_model
api_key_ns.models[api_key_response.name] = api_key_response
api_key_ns.models[api_key_all_response.name] = api_key_all_response
api_key_ns.models[api_key_model.name] = api_key_model
api_key_ns.models[key_permission_relation_create_model.name] = (
    key_permission_relation_create_model
)
api_key_ns.models[key_permission_relation_bulk_create_model.name] = (
    key_permission_relation_bulk_create_model
)
api_key_ns.models[key_permission_relation_bulk_delete_model.name] = (
    key_permission_relation_bulk_delete_model
)
api_key_ns.models[key_permission_relation_response.name] = (
    key_permission_relation_response
)
api_key_ns.models[key_permission_relation_model.name] = key_permission_relation_model
api_key_ns.models[key_permission_relation_msg_model.name] = (
    key_permission_relation_msg_model
)
api_key_ns.models[key_permission_relation_all_response.name] = (
    key_permission_relation_all_response
)
api_key_ns.models[key_permission_relation_bulk_response.name] = (
    key_permission_relation_bulk_response
)
api_key_ns.models[key_permission_relation_bulk_delete_response.name] = (
    key_permission_relation_bulk_delete_response
)
api_key_ns.models[permission_type_model.name] = permission_type_model
api_key_ns.models[permission_type_all_response.name] = permission_type_all_response


@api_key_ns.route("/generate")
class ApiKeyGenerate(Resource):
    @jwt_required()
    @admin_required
    @api_key_ns.expect(api_key_generate_model)
    @api_key_ns.marshal_with(api_key_generate_response)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        schema = ApiKeyGenerateSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while generating API key: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400

        try:
            from app.database.managers.api_keys_manager import ApiKeysManager

            db = ApiKeysManager()
            result = db.generate_api_key(
                name=data["name"],  # type: ignore
                expires_at=data["expires_at"],  # type: ignore
            )
            return {
                "msg": "API key generated successfully",
                "api_key_id": result["api_key_id"],
                "token": result["token"],
            }, 200
        except IntegrityError:
            return {"msg": "API key with this name already exists"}, 409
        except Exception as e:
            logger.error(
                f"Error generating API key: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error generating API key: {e}"}, 500


@api_key_ns.route("/all")
class ApiKeyAll(Resource):
    @jwt_required()
    @admin_required
    @api_key_ns.expect(api_key_filter_parser)
    @api_key_ns.marshal_with(api_key_all_response)
    def get(self):
        current_user = json.loads(get_jwt_identity())
        schema = ApiKeyFilterSchema()
        try:
            args = schema.load(request.args)
        except ValidationError as err:
            logger.error(
                f"Validation error while filtering API keys: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400

        try:
            from app.database.managers.api_keys_manager import ApiKeysManager

            db = ApiKeysManager()
            api_keys = db.get_all_public(
                offset=args.get("offset", 0),  # type: ignore
                limit=args.get("limit"),  # type: ignore
                sort_by=args.get("sort_by"),  # type: ignore
                sort_order=args.get("sort_order", "desc"),  # type: ignore
            )
            return {"msg": "API keys found successfully", "api_keys": api_keys}, 200
        except Exception as e:
            logger.error(f"Error fetching API keys: {e}", extra={"login": current_user})
            return {"msg": f"Error fetching API keys: {e}"}, 500


@api_key_ns.route("/<string:api_key_id>/view")
class ApiKeyView(Resource):
    @jwt_required()
    @admin_required
    @api_key_ns.marshal_with(api_key_response)
    def get(self, api_key_id):
        current_user = json.loads(get_jwt_identity())
        try:
            api_key_id = UUID(api_key_id)
        except ValueError:
            return {"msg": "Invalid API key ID format"}, 400

        try:
            from app.database.managers.api_keys_manager import ApiKeysManager

            db = ApiKeysManager()
            api_key = db.get_by_id_public(api_key_id=api_key_id)
            if not api_key:
                return {"msg": "API key not found"}, 404
            return {"msg": "API key found successfully", "api_key": api_key}, 200
        except Exception as e:
            logger.error(f"Error fetching API key: {e}", extra={"login": current_user})
            return {"msg": f"Error fetching API key: {e}"}, 500


@api_key_ns.route("/<string:api_key_id>/delete")
class ApiKeyDelete(Resource):
    @jwt_required()
    @admin_required
    @api_key_ns.marshal_with(api_key_msg_model)
    def delete(self, api_key_id):
        current_user = json.loads(get_jwt_identity())
        try:
            api_key_id = UUID(api_key_id)
        except ValueError:
            return {"msg": "Invalid API key ID format"}, 400

        try:
            from app.database.managers.api_keys_manager import ApiKeysManager

            db = ApiKeysManager()
            deleted = db.delete(record_id=api_key_id)
            if not deleted:
                return {"msg": "API key not found"}, 404
            return {
                "msg": "API key deleted successfully",
                "api_key_id": str(api_key_id),
            }, 200
        except IntegrityError:
            return {"msg": "Cannot delete API key: dependent data exists"}, 409
        except Exception as e:
            logger.error(f"Error deleting API key: {e}", extra={"login": current_user})
            return {"msg": f"Error deleting API key: {e}"}, 500


@api_key_ns.route("/permissions/add")
class KeyPermissionRelationAdd(Resource):
    @jwt_required()
    @admin_required
    @api_key_ns.expect(key_permission_relation_create_model)
    @api_key_ns.marshal_with(key_permission_relation_response)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        schema = KeyPermissionTypeRelationCreateSchema()
        try:
            data = schema.load(request.json)  # type: ignore
            api_key_id = UUID(data["api_key_id"])  # type: ignore
            permission_type_id = UUID(data["permission_type_id"])  # type: ignore
        except ValidationError as err:
            return {"error": err.messages}, 400
        except ValueError:
            return {"msg": "Invalid UUID format"}, 400

        try:
            from app.database.managers.key_permission_type_relations_manager import (
                KeyPermissionTypeRelationsManager,
            )

            db = KeyPermissionTypeRelationsManager()
            relation = db.add(
                api_key_id=api_key_id, permission_type_id=permission_type_id
            )
            return {"msg": "Relation added successfully", "relation": relation}, 200
        except IntegrityError:
            return {"msg": "Relation already exists or foreign key is invalid"}, 409
        except Exception as e:
            logger.error(f"Error adding relation: {e}", extra={"login": current_user})
            return {"msg": f"Error adding relation: {e}"}, 500


@api_key_ns.route("/permissions/add/many")
class KeyPermissionRelationAddMany(Resource):
    @jwt_required()
    @admin_required
    @api_key_ns.expect(key_permission_relation_bulk_create_model)
    @api_key_ns.marshal_with(key_permission_relation_bulk_response)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        schema = KeyPermissionTypeRelationBulkCreateSchema()
        try:
            data = schema.load(request.json)  # type: ignore
            api_key_id = UUID(data["api_key_id"])  # type: ignore
            permission_type_ids = [UUID(value) for value in data["permission_type_ids"]]  # type: ignore
        except ValidationError as err:
            return {"error": err.messages}, 400
        except ValueError:
            return {"msg": "Invalid UUID format"}, 400

        try:
            from app.database.managers.key_permission_type_relations_manager import (
                KeyPermissionTypeRelationsManager,
            )

            db = KeyPermissionTypeRelationsManager()
            relations = db.add_many(
                api_key_id=api_key_id, permission_type_ids=permission_type_ids
            )
            return {"msg": "Relations added successfully", "relations": relations}, 200
        except IntegrityError:
            return {
                "msg": "One or more relations already exist or foreign keys are invalid"
            }, 409
        except Exception as e:
            logger.error(
                f"Error adding relations in bulk: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error adding relations in bulk: {e}"}, 500


@api_key_ns.route("/permissions/all")
class KeyPermissionRelationAll(Resource):
    @jwt_required()
    @admin_required
    @api_key_ns.expect(key_permission_relation_filter_parser)
    @api_key_ns.marshal_with(key_permission_relation_all_response)
    def get(self):
        current_user = json.loads(get_jwt_identity())
        args = key_permission_relation_filter_parser.parse_args()
        filters = {}
        try:
            if args.get("api_key_id"):
                filters["api_key_id"] = UUID(args["api_key_id"])
            if args.get("permission_type_id"):
                filters["permission_type_id"] = UUID(args["permission_type_id"])
        except ValueError:
            return {"msg": "Invalid UUID format"}, 400

        try:
            from app.database.managers.key_permission_type_relations_manager import (
                KeyPermissionTypeRelationsManager,
            )

            db = KeyPermissionTypeRelationsManager()
            relations = db.get_all_filtered(
                offset=args.get("offset", 0),
                limit=args.get("limit"),
                sort_by=args.get("sort_by", "id"),
                sort_order=args.get("sort_order", "desc"),
                **filters,
            )
            return {"msg": "Relations found successfully", "relations": relations}, 200
        except Exception as e:
            logger.error(
                f"Error fetching relations: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error fetching relations: {e}"}, 500


@api_key_ns.route("/permissions/<string:relation_id>/view")
class KeyPermissionRelationView(Resource):
    @jwt_required()
    @admin_required
    @api_key_ns.marshal_with(key_permission_relation_response)
    def get(self, relation_id):
        current_user = json.loads(get_jwt_identity())
        try:
            relation_id = UUID(relation_id)
        except ValueError:
            return {"msg": "Invalid relation ID format"}, 400

        try:
            from app.database.managers.key_permission_type_relations_manager import (
                KeyPermissionTypeRelationsManager,
            )

            db = KeyPermissionTypeRelationsManager()
            relation = db.get_by_id(relation_id)
            if not relation:
                return {"msg": "Relation not found"}, 404
            return {"msg": "Relation found successfully", "relation": relation}, 200
        except Exception as e:
            logger.error(f"Error fetching relation: {e}", extra={"login": current_user})
            return {"msg": f"Error fetching relation: {e}"}, 500


@api_key_ns.route("/permissions/<string:relation_id>/delete")
class KeyPermissionRelationDelete(Resource):
    @jwt_required()
    @admin_required
    @api_key_ns.marshal_with(key_permission_relation_msg_model)
    def delete(self, relation_id):
        current_user = json.loads(get_jwt_identity())
        try:
            relation_id = UUID(relation_id)
        except ValueError:
            return {"msg": "Invalid relation ID format"}, 400

        try:
            from app.database.managers.key_permission_type_relations_manager import (
                KeyPermissionTypeRelationsManager,
            )

            db = KeyPermissionTypeRelationsManager()
            deleted = db.delete(record_id=relation_id)
            if not deleted:
                return {"msg": "Relation not found"}, 404
            return {"msg": "Relation deleted successfully", "id": str(relation_id)}, 200
        except Exception as e:
            logger.error(f"Error deleting relation: {e}", extra={"login": current_user})
            return {"msg": f"Error deleting relation: {e}"}, 500


@api_key_ns.route("/permissions/delete/many")
class KeyPermissionRelationDeleteMany(Resource):
    @jwt_required()
    @admin_required
    @api_key_ns.expect(key_permission_relation_bulk_delete_model)
    @api_key_ns.marshal_with(key_permission_relation_bulk_delete_response)
    def delete(self):
        current_user = json.loads(get_jwt_identity())
        schema = KeyPermissionTypeRelationBulkDeleteSchema()
        try:
            data = schema.load(request.json)  # type: ignore
            relation_ids = [UUID(value) for value in data["relation_ids"]]  # type: ignore
        except ValidationError as err:
            return {"error": err.messages}, 400
        except ValueError:
            return {"msg": "Invalid UUID format"}, 400

        try:
            from app.database.managers.key_permission_type_relations_manager import (
                KeyPermissionTypeRelationsManager,
            )

            db = KeyPermissionTypeRelationsManager()
            deleted_ids = db.delete_many(relation_ids=relation_ids)
            return {
                "msg": "Relations deleted successfully",
                "deleted_ids": deleted_ids,
                "deleted_count": len(deleted_ids),
            }, 200
        except Exception as e:
            logger.error(
                f"Error deleting relations in bulk: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error deleting relations in bulk: {e}"}, 500


@api_key_ns.route("/permission-types/all")
class PermissionTypeAll(Resource):
    @jwt_required()
    @admin_required
    @api_key_ns.expect(permission_type_filter_parser)
    @api_key_ns.marshal_with(permission_type_all_response)
    def get(self):
        current_user = json.loads(get_jwt_identity())
        schema = PermissionTypeFilterSchema()
        try:
            args = schema.load(request.args)
        except ValidationError as err:
            return {"msg": f"Invalid permission type filter: {err.messages}"}, 400

        try:
            from app.database.managers.key_permission_type_relations_manager import (
                KeyPermissionTypeRelationsManager,
            )

            db = KeyPermissionTypeRelationsManager()
            permission_types = db.get_permission_types_all(
                offset=args.get("offset", 0),  # type: ignore
                limit=args.get("limit"),  # type: ignore
                sort_by=args.get("sort_by", "code"),  # type: ignore
                sort_order=args.get("sort_order", "asc"),  # type: ignore
            )
            return {
                "msg": "Permission types found successfully",
                "permission_types": permission_types,
            }, 200
        except Exception as e:
            logger.error(
                f"Error fetching permission types: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error fetching permission types: {e}"}, 500
