"""Standard API response helpers."""

from flask import jsonify


def ok(data: dict | None = None, status_code: int = 200):
    payload = data or {}
    response = jsonify(payload)
    response.status_code = status_code
    return response
