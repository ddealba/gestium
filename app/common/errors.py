"""Error handlers for the application."""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


SPECIAL_ERROR_RESPONSES = {
    "tenant_context_required": {
        "code": "tenant_context_required",
        "message": "Selecciona un tenant",
        "status": 400,
    },
    "tenant_not_found": {
        "code": "tenant_not_found",
        "message": "Tenant no encontrado",
        "status": 404,
    },
}

def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the app."""

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        special_error = SPECIAL_ERROR_RESPONSES.get(str(error.description))
        if special_error:
            response = jsonify({
                "error": {
                    "code": special_error["code"],
                    "message": special_error["message"],
                }
            })
            response.status_code = special_error["status"]
            return response

        response = jsonify({
            "error": error.name,
            "message": error.description,
        })
        response.status_code = error.code or 500
        return response

    @app.errorhandler(Exception)
    def handle_unexpected_exception(error: Exception):
        response = jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred.",
        })
        response.status_code = 500
        return response
