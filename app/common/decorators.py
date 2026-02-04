"""Shared decorators for routes or services."""

from functools import wraps
from typing import Any, Callable

from flask import g, request
from werkzeug.exceptions import Forbidden, Unauthorized

from app.common.jwt import decode_token
from app.repositories.user_repository import UserRepository


def noop_decorator(func: Callable):
    """Placeholder decorator for future cross-cutting concerns."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def auth_required(func: Callable[..., Any]):
    """Ensure the request has a valid bearer token and active user."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        auth_header = request.headers.get("Authorization", "")
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise Unauthorized("missing_token")

        payload = decode_token(parts[1])
        user_id = payload.get("sub")
        client_id = payload.get("client_id")
        if not user_id or not client_id:
            raise Unauthorized("invalid_token")

        user = UserRepository().get_by_id(str(user_id), str(client_id))
        if user is None:
            raise Unauthorized("invalid_credentials")
        if user.status != "active":
            raise Forbidden("user_inactive")

        g.user = user
        g.client_id = user.client_id
        return func(*args, **kwargs)

    return wrapper
