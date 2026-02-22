"""Tenant admin routes for users and roles."""

from __future__ import annotations

from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest, Forbidden

from app.common.authz import AuthorizationService
from app.common.decorators import auth_required
from app.common.responses import ok
from app.extensions import db
from app.modules.admin.service import TenantAdminService

bp = Blueprint("admin", __name__)


def _require_any_permission(*permission_codes: str) -> None:
    authz = AuthorizationService()
    if any(authz.user_has_permission(g.user, code) for code in permission_codes):
        return
    raise Forbidden("missing_permission")


def _serialize_user(user) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "status": user.status,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "roles": [
            {
                "id": role.id,
                "name": role.name,
                "scope": role.scope,
            }
            for role in sorted(user.roles, key=lambda value: value.name)
        ],
    }


@bp.get("/admin/users")
@auth_required
def list_users():
    _require_any_permission("tenant.user.read", "tenant.users.manage")
    page = request.args.get("page", type=int)
    per_page = request.args.get("per_page", type=int)

    service = TenantAdminService()
    result = service.list_users(str(g.client_id), page=page, per_page=per_page)
    return ok(
        {
            "items": [_serialize_user(user) for user in result.items],
            "total": result.total,
            "page": result.page,
            "per_page": result.per_page,
        }
    )


@bp.post("/admin/users/invite")
@auth_required
def invite_user():
    _require_any_permission("tenant.user.invite", "tenant.users.invite")
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    if not email:
        raise BadRequest("email_required")

    service = TenantAdminService()
    result = service.invite_user(
        str(g.client_id),
        email,
        role_ids=payload.get("role_ids"),
        role_names=payload.get("role_names") or payload.get("roles"),
    )
    db.session.commit()

    return ok(
        {
            "id": result.invitation.id,
            "email": result.invitation.email,
            "status": "invited",
            "activation_link": f"/auth/activate?token={result.token}",
        },
        status_code=201,
    )


@bp.post("/admin/users/<user_id>/disable")
@auth_required
def disable_user(user_id: str):
    _require_any_permission("tenant.user.manage", "tenant.users.manage")
    service = TenantAdminService()
    user = service.disable_user(str(g.client_id), user_id)
    db.session.commit()
    return ok(_serialize_user(user))


@bp.post("/admin/users/<user_id>/enable")
@auth_required
def enable_user(user_id: str):
    _require_any_permission("tenant.user.manage", "tenant.users.manage")
    service = TenantAdminService()
    user = service.enable_user(str(g.client_id), user_id)
    db.session.commit()
    return ok(_serialize_user(user))


@bp.put("/admin/users/<user_id>/roles")
@auth_required
def replace_user_roles(user_id: str):
    _require_any_permission("tenant.user.manage", "tenant.users.manage")
    payload = request.get_json(silent=True) or {}
    service = TenantAdminService()
    roles = service.replace_roles(
        str(g.client_id),
        user_id,
        role_ids=payload.get("role_ids"),
        role_names=payload.get("role_names") or payload.get("roles"),
    )
    db.session.commit()
    return ok(
        {
            "user_id": user_id,
            "roles": [{"id": role.id, "name": role.name, "scope": role.scope} for role in roles],
        }
    )


@bp.get("/admin/roles")
@auth_required
def list_roles():
    _require_any_permission("tenant.role.read", "tenant.users.manage")
    service = TenantAdminService()
    roles = service.list_roles(str(g.client_id))
    return ok({"items": [{"id": role.id, "name": role.name, "scope": role.scope} for role in roles]})
