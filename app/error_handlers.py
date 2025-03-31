import logging
from flask import jsonify, request


logger = logging.getLogger('ok_service')


def get_anonymous_login():
    return {
        "user_id": "anonymous",
        "login": request.remote_addr,
        "role": "unknown"
    }


def setup_error_handlers(app):

    # @app.errorhandler(NoAuthorizationError)
    # @app.errorhandler(401)
    # def handle_unauthorized(e):
    #     logger.warning("401 Unauthorized", extra={
    #                    "login": get_anonymous_login()})
    #     return jsonify({"msg": "Unauthorized"}), 401

    # @app.errorhandler(403)
    # def handle_forbidden(e):
    #     logger.warning("403 Forbidden", extra={"login": get_anonymous_login()})
    #     return jsonify({"msg": "Forbidden"}), 403

    @app.errorhandler(404)
    def handle_not_found(e):
        logger.warning(f"404 Not Found: {request.path}", extra={
                       "login": get_anonymous_login()})
        return jsonify({"msg": "Not Found"}), 404

    # @app.errorhandler(409)
    # def handle_conflict(e):
    #     logger.warning(f"409 Conflict: {request.path}", extra={
    #                    "login": get_anonymous_login()})
    #     return jsonify({"msg": "Conflict"}), 404

    # @app.errorhandler(HTTPException)
    # def handle_http_exception(e):
    #     logger.warning(f"HTTPException {e.code}: {e.description}", extra={
    #                    "login": get_anonymous_login()})
    #     return jsonify({"msg": e.description}), e.code

    # @app.errorhandler(Exception)
    # def handle_unexpected_error(e):
    #     logger.error(f"Unhandled error: {e}", extra={
    #                  "login": get_anonymous_login()})
    #     return jsonify({"msg": "Internal server error"}), 500
