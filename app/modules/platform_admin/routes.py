"""Routes for platform-level tenant administration."""

from __future__ import annotations

from flask import Blueprint, request
from werkzeug.exceptions import BadRequest

from app.common.decorators import auth_required, require_permission
from app.common.responses import ok
from app.extensions import db
from app.modules.platform_admin.service import PlatformAdminService

bp = Blueprint("platform_admin", __name__)


def _parse_int_arg(name: str, default: int) -> int:
    raw_value = request.args.get(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise BadRequest(f"invalid_{name}") from exc


@bp.get("/platform/tenants")
@auth_required
@require_permission("platform.super_admin")
def list_tenants():
    limit = _parse_int_arg("limit", 50)
    offset = _parse_int_arg("offset", 0)
    service = PlatformAdminService()
    items, total = service.list_tenants(
        q=request.args.get("q"),
        status=request.args.get("status"),
        limit=limit,
        offset=offset,
    )
    return ok({
        "items": items,
        "total": total,
        "limit": max(limit, 1),
        "offset": max(offset, 0),
    })




@bp.get("/platform/tenants/<tenant_id>")
@auth_required
@require_permission("platform.super_admin")
def get_tenant_detail(tenant_id: str):
    service = PlatformAdminService()
    tenant = service.get_tenant_detail(tenant_id)
    return ok({"tenant": tenant})

@bp.post("/platform/tenants")
@auth_required
@require_permission("platform.super_admin")
def create_tenant():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        raise BadRequest("name_required")

    service = PlatformAdminService()
    tenant = service.create_tenant(payload)
    db.session.commit()
    return ok(
        {
            "tenant": {
                "id": tenant.id,
                "name": tenant.name,
                "status": tenant.status,
                "plan": tenant.plan,
                "logo_url": getattr(tenant, "logo_url", None),
                "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
            }
        },
        status_code=201,
    )


@bp.patch("/platform/tenants/<tenant_id>")
@auth_required
@require_permission("platform.super_admin")
def update_tenant(tenant_id: str):
    payload = request.get_json(silent=True) or {}
    service = PlatformAdminService()
    tenant = service.update_tenant(tenant_id, payload)
    db.session.commit()
    return ok(
        {
            "tenant": {
                "id": tenant.id,
                "name": tenant.name,
                "status": tenant.status,
                "plan": tenant.plan,
                "logo_url": getattr(tenant, "logo_url", None),
                "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
            }
        }
    )
