"""Shared decorators for routes or services."""

from functools import wraps
from typing import Any, Callable

from flask import g, request
from werkzeug.exceptions import Forbidden, Unauthorized

from app.common.acl import resolve_company_id
from app.common.authz import AuthorizationService
from app.common.jwt import decode_token
from app.repositories.user_repository import UserRepository
from app.services.company_access_service import CompanyAccessService


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


def require_permission(code: str):
    """Ensure the request has a valid user with the required permission."""

    def decorator(func: Callable[..., Any]):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            if not getattr(g, "user", None):
                raise Unauthorized("missing_token")
            if not AuthorizationService().user_has_permission(g.user, code):
                raise Forbidden("missing_permission")
            return func(*args, **kwargs)

        return wrapper

    return decorator


def require_company_access(required_level: str, company_id_arg: str | None = None):
    """Ensure the request user has the required company ACL access level."""

    def decorator(func: Callable[..., Any]):
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):
            if not getattr(g, "user", None):
                raise Unauthorized("missing_token")
            company_id = resolve_company_id(company_id_arg)
            service = CompanyAccessService()
            service.require_access(
                user_id=str(g.user.id),
                company_id=str(company_id),
                client_id=str(g.client_id),
                required_level=required_level,
            )
            return func(*args, **kwargs)

        return wrapper

    return decorator
