"""Tenant context middleware and helpers."""

from __future__ import annotations

from functools import wraps
import uuid
from typing import Any, Callable

from flask import Flask, current_app, g, request
from werkzeug.exceptions import BadRequest, NotFound

from app.common.authz import AuthorizationService
from app.models.client import Client
from app.modules.audit.audit_service import AuditService

CLIENT_ID_HEADER = "X-Client-Id"
ADMIN_TENANT_HEADER = "X-Admin-Tenant"


def register_tenant_context(app: Flask) -> None:
    """Register tenant context resolution for each request."""

    @app.before_request
    def _resolve_tenant_context() -> None:
        refresh_tenant_context()


def refresh_tenant_context() -> None:
    """Refresh tenant context based on current request/user."""
    g.tenant_mode = "tenant_context"
    g.client_id = _resolve_client_id()


def _resolve_client_id() -> uuid.UUID | None:
    """Resolve the tenant client_id from auth or headers."""
    user = getattr(g, "user", None)
    if user is not None:
        authz = AuthorizationService()
        if authz.is_super_admin(user):
            header_tenant_id = request.headers.get(ADMIN_TENANT_HEADER)
            if not header_tenant_id:
                g.tenant_mode = "platform_no_context"
                return None
            tenant_id = _parse_client_id(header_tenant_id)
            tenant = Client.query.filter_by(id=str(tenant_id)).first()
            if tenant is None:
                raise NotFound("tenant_not_found")
            g.tenant_mode = "platform_context"
            AuditService().log_action(
                client_id=str(tenant_id),
                actor_user_id=str(user.id),
                action="platform_tenant_context_used",
                entity_type="tenant",
                entity_id=str(tenant_id),
                metadata={"tenant_id": str(tenant_id), "path": request.path, "method": request.method},
            )
            return tenant_id

        user_client_id = getattr(user, "client_id", None)
        if user_client_id:
            g.tenant_mode = "tenant_context"
            return _parse_client_id(user_client_id)

    if current_app.config.get("ALLOW_X_CLIENT_ID_HEADER", False):
        header_value = request.headers.get(CLIENT_ID_HEADER)
        if header_value:
            g.tenant_mode = "tenant_context"
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


def tenant_context_required(func: Callable[..., Any]):
    """Ensure tenant context exists for tenant-scoped resources."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        if getattr(g, "client_id", None) is None:
            raise BadRequest("tenant_context_required")
        return func(*args, **kwargs)

    return wrapper


def tenant_required(func: Callable[..., Any]):
    """Backward compatible alias for tenant context checks."""

    return tenant_context_required(func)


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
