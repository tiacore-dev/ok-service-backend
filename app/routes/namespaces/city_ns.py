import json
import logging
from uuid import UUID

from flask import abort, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.decorators import admin_required
from app.routes.models.city_models import (
    city_all_response,
    city_create_model,
    city_filter_parser,
    city_model,
    city_msg_model,
    city_response,
)
from app.schemas.city_schemas import CityCreateSchema, CityEditSchema, CityFilterSchema

logger = logging.getLogger("ok_service")

city_ns = Namespace("cities", description="City management operations")

city_ns.models[city_create_model.name] = city_create_model
city_ns.models[city_msg_model.name] = city_msg_model
city_ns.models[city_response.name] = city_response
city_ns.models[city_all_response.name] = city_all_response
city_ns.models[city_model.name] = city_model


@city_ns.route("/add")
class CityAdd(Resource):
    @jwt_required()
    @admin_required
    @city_ns.expect(city_create_model)
    @city_ns.marshal_with(city_msg_model)
    def post(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to add new city", extra={"login": current_user})

        schema = CityCreateSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while adding city: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400

        name = data.get("name")  # type: ignore

        from app.database.managers.cities_manager import CitiesManager

        db = CitiesManager()

        if db.exists(name=name):
            logger.warning(
                f"City with name '{name}' already exists",
                extra={"login": current_user},
            )
            return {"msg": "City already exists"}, 409

        try:
            new_city = db.add(created_by=current_user["user_id"], name=name)  # type: ignore
            logger.info(
                f"New city added: {new_city['city_id']}",
                extra={"login": current_user},
            )
            return {
                "msg": "New city added successfully",
                "city_id": new_city["city_id"],
            }, 200
        except Exception as e:
            logger.error(f"Error adding city: {e}", extra={"login": current_user})
            return {"msg": f"Error adding city: {e}"}, 500


@city_ns.route("/<string:city_id>/view")
class CityView(Resource):
    @jwt_required()
    @city_ns.marshal_with(city_response)
    def get(self, city_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Request to view city: {city_id}", extra={"login": current_user})

        try:
            try:
                city_uuid = UUID(city_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.cities_manager import CitiesManager

            db = CitiesManager()
            city = db.get_by_id(city_uuid)
            if not city:
                logger.warning(
                    f"City {city_id} not found", extra={"login": current_user}
                )
                return {"msg": "City not found"}, 404
            return {"msg": "City found successfully", "city": city}, 200
        except Exception as e:
            logger.error(f"Error viewing city: {e}", extra={"login": current_user})
            return {"msg": f"Error viewing city: {e}"}, 500


@city_ns.route("/<string:city_id>/delete/soft")
class CitySoftDelete(Resource):
    @jwt_required()
    @admin_required
    @city_ns.marshal_with(city_msg_model)
    def patch(self, city_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to soft delete city: {city_id}", extra={"login": current_user}
        )

        try:
            try:
                city_uuid = UUID(city_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.cities_manager import CitiesManager

            db = CitiesManager()
            updated = db.update(record_id=city_uuid, deleted=True)
            if not updated:
                logger.warning(
                    f"City {city_id} not found for soft delete",
                    extra={"login": current_user},
                )
                return {"msg": "City not found"}, 404
            return {
                "msg": f"City {city_id} soft deleted successfully",
                "city_id": city_id,
            }, 200
        except Exception as e:
            logger.error(
                f"Error soft deleting city: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error soft deleting city: {e}"}, 500


@city_ns.route("/<string:city_id>/delete/hard")
class CityHardDelete(Resource):
    @jwt_required()
    @admin_required
    @city_ns.marshal_with(city_msg_model)
    def delete(self, city_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(
            f"Request to hard delete city: {city_id}", extra={"login": current_user}
        )

        try:
            try:
                city_uuid = UUID(city_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.cities_manager import CitiesManager

            db = CitiesManager()
            deleted = db.delete(record_id=city_uuid)
            if not deleted:
                logger.warning(
                    f"City {city_id} not found for hard delete",
                    extra={"login": current_user},
                )
                return {"msg": "City not found"}, 404
            return {
                "msg": f"City {city_id} hard deleted successfully",
                "city_id": city_id,
            }, 200
        except IntegrityError:
            logger.warning(
                f"Cannot hard delete city {city_id}: dependent data exists",
                extra={"login": current_user},
            )
            abort(409, description="Cannot delete city: dependent data exists.")
        except Exception as e:
            logger.error(
                f"Error hard deleting city: {e}", extra={"login": current_user}
            )
            return {"msg": f"Error hard deleting city: {e}"}, 500


@city_ns.route("/<string:city_id>/edit")
class CityEdit(Resource):
    @jwt_required()
    @admin_required
    @city_ns.expect(city_create_model)
    @city_ns.marshal_with(city_msg_model)
    def patch(self, city_id):
        current_user = json.loads(get_jwt_identity())
        logger.info(f"Request to edit city: {city_id}", extra={"login": current_user})

        schema = CityEditSchema()
        try:
            data = schema.load(request.json)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while editing city: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400

        updates = {}
        if "name" in data:  # type: ignore
            if not data["name"]:  # type: ignore
                logger.warning(
                    "Attempt to set empty name for city",
                    extra={"login": current_user},
                )
                return {"msg": "Bad request, invalid data."}, 400
            updates["name"] = data["name"]  # type: ignore
        if "deleted" in data:  # type: ignore
            updates["deleted"] = data["deleted"]  # type: ignore

        if not updates:
            logger.warning(
                "No valid fields provided for city update",
                extra={"login": current_user},
            )
            return {"msg": "No data provided for update"}, 400

        try:
            try:
                city_uuid = UUID(city_id)
            except ValueError as exc:
                raise ValueError("Invalid UUID format") from exc

            from app.database.managers.cities_manager import CitiesManager

            db = CitiesManager()

            if "name" in updates and db.exists(name=updates["name"]):
                existing = db.filter_one_by_dict(name=updates["name"])
                if existing and existing["city_id"] != city_id:
                    logger.warning(
                        f"City with name '{updates['name']}' already exists",
                        extra={"login": current_user},
                    )
                    return {"msg": "City already exists"}, 409

            updated = db.update(record_id=city_uuid, **updates)
            if not updated:
                logger.warning(
                    f"City {city_id} not found for editing",
                    extra={"login": current_user},
                )
                return {"msg": "City not found"}, 404
            return {"msg": "City edited successfully", "city_id": city_id}, 200
        except Exception as e:
            logger.error(f"Error editing city: {e}", extra={"login": current_user})
            return {"msg": f"Error editing city: {e}"}, 500


@city_ns.route("/all")
class CityAll(Resource):
    @jwt_required()
    @city_ns.expect(city_filter_parser)
    @city_ns.marshal_with(city_all_response)
    def get(self):
        current_user = json.loads(get_jwt_identity())
        logger.info("Request to fetch all cities", extra={"login": current_user})

        schema = CityFilterSchema()
        try:
            args = schema.load(request.args)  # type: ignore
        except ValidationError as err:
            logger.error(
                f"Validation error while filtering cities: {err.messages}",
                extra={"login": current_user},
            )
            return {"error": err.messages}, 400

        offset = args.get("offset", 0)  # type: ignore
        limit = args.get("limit", 10)  # type: ignore
        sort_by = args.get("sort_by")  # type: ignore
        sort_order = args.get("sort_order", "desc")  # type: ignore
        filters = {
            "name": args.get("name"),  # type: ignore
            "deleted": args.get("deleted"),  # type: ignore
        }

        try:
            from app.database.managers.cities_manager import CitiesManager

            db = CitiesManager()
            cities = db.get_all_filtered(
                offset=offset,
                limit=limit,
                sort_by=sort_by,  # type: ignore
                sort_order=sort_order,
                **filters,
            )
            logger.info(
                f"Successfully fetched {len(cities)} cities",
                extra={"login": current_user},
            )
            return {"msg": "Cities found successfully", "cities": cities}, 200
        except Exception as e:
            logger.error(f"Error fetching cities: {e}", extra={"login": current_user})
            return {"msg": f"Error fetching cities: {e}"}, 500
