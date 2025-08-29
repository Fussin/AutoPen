from functools import wraps
from flask import request, jsonify
from .models import User

def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"message": "API key is missing"}), 401

        user = User.query.filter_by(api_key=api_key).first()
        if not user:
            return jsonify({"message": "Invalid API key"}), 401

        return f(*args, **kwargs)
    return decorated_function
