"""RBAC routes."""

from flask import Blueprint, g

from app.common.authz import AuthorizationService
from app.common.decorators import auth_required, require_permission
from app.common.responses import ok

bp = Blueprint("rbac", __name__)


@bp.get("/rbac/me/permissions")
@auth_required
def list_my_permissions():
    service = AuthorizationService()
    permissions = sorted(service.get_user_permissions(g.user.id, g.client_id))
    return ok({"permissions": permissions})


@bp.get("/rbac/probe/company-write")
@auth_required
@require_permission("company.write")
def probe_company_write():
    return ok({"ok": True})
