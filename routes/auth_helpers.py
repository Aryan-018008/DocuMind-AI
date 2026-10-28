
from functools import wraps

from flask import jsonify, session


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("user_id"):
            return jsonify({
                "error": "Please log in to continue.",
                "redirect": "/login"
            }), 401

        return view(*args, **kwargs)

    return wrapped_view
