from functools import wraps

from flask import current_app, jsonify, request
from flask_login import current_user


def require_api_key(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        provided = request.headers.get("X-API-Key")
        if not provided or provided != current_app.config["API_KEY"]:
            return jsonify({"error": "unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return current_app.login_manager.unauthorized()
        return view(*args, **kwargs)

    return wrapped
