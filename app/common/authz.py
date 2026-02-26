"""Authorization helpers for RBAC permissions."""

from __future__ import annotations

from flask import g, has_request_context
from sqlalchemy import and_, or_

from app.extensions import db
from app.models.permission import Permission
from app.models.rbac import role_permissions, user_roles
from app.models.role import Role


class AuthorizationService:
    """Service for resolving permissions and authorization checks."""

    _CACHE_ATTR = "_authz_cache"

    def get_user_permissions(self, user_id: str, client_id: str) -> set[str]:
        """Resolve all permission codes for the user within platform + tenant scope."""
        cache = self._get_request_cache()
        cache_key = ("permissions", user_id, client_id)
        if cache_key in cache:
            return cache[cache_key]

        if self._user_is_super_admin(user_id):
            permissions = {code for (code,) in db.session.query(Permission.code).all()}
            cache[cache_key] = permissions
            return permissions

        query = (
            db.session.query(Permission.code)
            .join(role_permissions, Permission.id == role_permissions.c.permission_id)
            .join(Role, Role.id == role_permissions.c.role_id)
            .join(user_roles, user_roles.c.role_id == Role.id)
            .filter(user_roles.c.user_id == user_id)
            .filter(
                or_(
                    Role.scope == "platform",
                    and_(Role.scope == "tenant", Role.client_id == client_id),
                )
            )
            .distinct()
        )
        permissions = {code for (code,) in query.all()}
        cache[cache_key] = permissions
        return permissions

    def user_has_permission(self, user, permission_code: str) -> bool:
        """Return True if the user has the permission code (or is Super Admin)."""
        if user is None:
            return False
        if self._user_is_super_admin(user.id):
            return True
        permissions = self.get_user_permissions(user.id, user.client_id)
        return permission_code in permissions

    def is_super_admin(self, user) -> bool:
        """Return True when the user is global Super Admin or has explicit permission."""
        if user is None:
            return False
        if self._user_is_super_admin(user.id):
            return True
        permissions = self.get_user_permissions(user.id, user.client_id)
        return "platform.super_admin" in permissions

    def _user_is_super_admin(self, user_id: str) -> bool:
        cache = self._get_request_cache()
        cache_key = ("super_admin", user_id)
        if cache_key in cache:
            return cache[cache_key]

        exists = (
            db.session.query(Role.id)
            .join(user_roles, user_roles.c.role_id == Role.id)
            .filter(
                user_roles.c.user_id == user_id,
                Role.scope == "platform",
                Role.name == "Super Admin",
            )
            .first()
            is not None
        )
        cache[cache_key] = exists
        return exists

    def _get_request_cache(self) -> dict:
        if has_request_context():
            cache = getattr(g, self._CACHE_ATTR, None)
            if cache is None:
                cache = {}
                setattr(g, self._CACHE_ATTR, cache)
            return cache
        return {}
