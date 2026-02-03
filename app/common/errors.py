"""Error handlers for the application."""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app: Flask) -> None:
    """Register error handlers for the app."""

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
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
