import json
import logging
from uuid import UUID

from flask import request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.decorators import admin_required
from app.routes.models.api_key_models import (
    api_key_all_response,
    api_key_filter_parser,
    api_key_generate_model,
    api_key_generate_response,
    api_key_model,
    api_key_msg_model,
    api_key_response,
)
from app.schemas.api_key_schemas import ApiKeyFilterSchema, ApiKeyGenerateSchema

logger = logging.getLogger("ok_service")

api_key_ns = Namespace("api-key", description="API keys management operations")

api_key_ns.models[api_key_generate_model.name] = api_key_generate_model
api_key_ns.models[api_key_generate_response.name] = api_key_generate_response
api_key_ns.models[api_key_msg_model.name] = api_key_msg_model
api_key_ns.models[api_key_response.name] = api_key_response
api_key_ns.models[api_key_all_response.name] = api_key_all_response
api_key_ns.models[api_key_model.name] = api_key_model


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
