from functools import wraps
from flask import jsonify, request, current_app


def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('API-Key')
        if not api_key:
            return jsonify({"error": "API key is missing"}), 400
        if api_key != current_app.config['API_KEY']:
            return jsonify({"error": "Invalid API key"}), 403
        return f(*args, **kwargs)
    return decorated_function
