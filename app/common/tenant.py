"""Tenant context middleware and helpers."""

from __future__ import annotations

from functools import wraps
import uuid
from typing import Any, Callable

from flask import Flask, current_app, g, request
from werkzeug.exceptions import BadRequest, NotFound

CLIENT_ID_HEADER = "X-Client-Id"


def register_tenant_context(app: Flask) -> None:
    """Register tenant context resolution for each request."""

    @app.before_request
    def _resolve_tenant_context() -> None:
        g.client_id = _resolve_client_id()


def _resolve_client_id() -> uuid.UUID | None:
    """Resolve the tenant client_id from auth or headers."""
    user = getattr(g, "user", None)
    if user is not None:
        user_client_id = getattr(user, "client_id", None)
        if user_client_id:
            return _parse_client_id(user_client_id)

    if current_app.config.get("ALLOW_X_CLIENT_ID_HEADER", False):
        header_value = request.headers.get(CLIENT_ID_HEADER)
        if header_value:
            return _parse_client_id(header_value)

    return None


def _parse_client_id(value: Any) -> uuid.UUID:
    """Parse and validate a UUID value."""
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise BadRequest("Invalid client_id format.") from exc


def tenant_required(func: Callable[..., Any]):
    """Ensure the request has a resolved tenant client_id."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        if getattr(g, "client_id", None) is None:
            raise BadRequest("client_id is required for this resource.")
        return func(*args, **kwargs)

    return wrapper


def filter_by_client(query, client_id: uuid.UUID):
    """Filter a SQLAlchemy query by client_id."""
    model = None
    if hasattr(query, "column_descriptions"):
        if query.column_descriptions:
            model = query.column_descriptions[0].get("entity")
    if model is None or not hasattr(model, "client_id"):
        raise ValueError("Query model does not define client_id.")
    return query.filter(model.client_id == client_id)


def ensure_tenant(entity: Any, client_id: uuid.UUID):
    """Ensure the entity belongs to the provided tenant client_id."""
    if entity is None:
        raise NotFound("Resource not found.")
    if not hasattr(entity, "client_id"):
        raise ValueError("Entity does not define client_id.")
    if entity.client_id != client_id:
        raise NotFound("Resource not found.")
    return entity
