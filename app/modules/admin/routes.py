"""Tenant admin routes for users and roles."""

from __future__ import annotations

from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest, Forbidden

from app.common.access_levels import AccessLevel

from app.common.authz import AuthorizationService
from app.common.decorators import auth_required
from app.common.tenant import tenant_context_required
from app.common.responses import ok
from app.extensions import db
from app.modules.admin.service import TenantAdminService
from app.modules.audit.audit_service import AuditService
from app.services.company_access_service import CompanyAccessService

bp = Blueprint("admin", __name__)


def _safe_int_arg(name: str, default: int) -> int:
    value = request.args.get(name, type=int)
    if value is None:
        return default
    if value < 0:
        raise BadRequest(f"invalid_{name}")
    return value


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
@tenant_context_required
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
@tenant_context_required
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
    invited_user = service.user_repository.get_by_email(result.invitation.email, str(g.client_id))
    AuditService().log_action(
        client_id=str(g.client_id),
        actor_user_id=str(g.user.id),
        action="invite_user",
        entity_type="user",
        entity_id=invited_user.id if invited_user else result.invitation.id,
        metadata={"email": result.invitation.email},
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
@tenant_context_required
def disable_user(user_id: str):
    _require_any_permission("tenant.user.manage", "tenant.users.manage")
    service = TenantAdminService()
    user = service.disable_user(str(g.client_id), user_id)
    AuditService().log_action(
        client_id=str(g.client_id),
        actor_user_id=str(g.user.id),
        action="disable_user",
        entity_type="user",
        entity_id=user.id,
        metadata={"status": user.status},
    )
    db.session.commit()
    return ok(_serialize_user(user))


@bp.post("/admin/users/<user_id>/enable")
@auth_required
@tenant_context_required
def enable_user(user_id: str):
    _require_any_permission("tenant.user.manage", "tenant.users.manage")
    service = TenantAdminService()
    user = service.enable_user(str(g.client_id), user_id)
    AuditService().log_action(
        client_id=str(g.client_id),
        actor_user_id=str(g.user.id),
        action="enable_user",
        entity_type="user",
        entity_id=user.id,
        metadata={"status": user.status},
    )
    db.session.commit()
    return ok(_serialize_user(user))


@bp.put("/admin/users/<user_id>/roles")
@auth_required
@tenant_context_required
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
    AuditService().log_action(
        client_id=str(g.client_id),
        actor_user_id=str(g.user.id),
        action="change_roles",
        entity_type="user",
        entity_id=user_id,
        metadata={"roles": [role.name for role in roles]},
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
@tenant_context_required
def list_roles():
    _require_any_permission("tenant.role.read", "tenant.users.manage")
    service = TenantAdminService()
    roles = service.list_roles(str(g.client_id))
    return ok({"items": [{"id": role.id, "name": role.name, "scope": role.scope} for role in roles]})


@bp.get("/admin/companies")
@auth_required
@tenant_context_required
def list_admin_companies():
    _require_any_permission("company.read", "tenant.company.read")
    page = request.args.get("page", type=int)
    per_page = request.args.get("per_page", type=int)

    service = TenantAdminService()
    companies = service.company_repository.list(str(g.client_id))

    if page and per_page:
        if page < 1 or per_page < 1:
            raise BadRequest("invalid_pagination")
        total = len(companies)
        start = (page - 1) * per_page
        items = companies[start : start + per_page]
    else:
        total = len(companies)
        page = 1
        per_page = total or 1
        items = companies

    return ok(
        {
            "items": [
                {
                    "id": company.id,
                    "name": company.name,
                    "tax_id": company.tax_id,
                    "status": company.status,
                }
                for company in items
            ],
            "total": total,
            "page": page,
            "per_page": per_page,
        }
    )


@bp.get("/admin/companies/<company_id>/access")
@auth_required
@tenant_context_required
def list_company_access(company_id: str):
    _require_any_permission("acl.read")
    service = TenantAdminService()
    CompanyAccessService(service.access_repository).require_access(
        user_id=str(g.user.id),
        company_id=company_id,
        client_id=str(g.client_id),
        required_level=AccessLevel.admin.value,
    )
    items = service.list_company_accesses(str(g.client_id), company_id)
    return ok({"items": items})


@bp.post("/admin/companies/<company_id>/access")
@auth_required
@tenant_context_required
def upsert_company_access(company_id: str):
    _require_any_permission("acl.manage")
    payload = request.get_json(silent=True) or {}
    access_level = payload.get("access_level")
    user_id = payload.get("user_id")
    if not user_id or not access_level:
        raise BadRequest("invalid_payload")
    if access_level not in {level.value for level in AccessLevel}:
        raise BadRequest("invalid_access_level")

    service = TenantAdminService()
    CompanyAccessService(service.access_repository).require_access(
        user_id=str(g.user.id),
        company_id=company_id,
        client_id=str(g.client_id),
        required_level=AccessLevel.admin.value,
    )
    item = service.upsert_company_access(str(g.client_id), company_id, user_id, access_level)
    AuditService().log_action(
        client_id=str(g.client_id),
        actor_user_id=str(g.user.id),
        action="assign_acl",
        entity_type="company",
        entity_id=company_id,
        metadata={"user_id": user_id, "access_level": access_level},
    )
    db.session.commit()
    return ok(item, status_code=201)


@bp.patch("/admin/companies/<company_id>/access/<user_id>")
@auth_required
@tenant_context_required
def patch_company_access(company_id: str, user_id: str):
    _require_any_permission("acl.manage")
    payload = request.get_json(silent=True) or {}
    access_level = payload.get("access_level")
    if not access_level:
        raise BadRequest("invalid_payload")
    if access_level not in {level.value for level in AccessLevel}:
        raise BadRequest("invalid_access_level")

    service = TenantAdminService()
    CompanyAccessService(service.access_repository).require_access(
        user_id=str(g.user.id),
        company_id=company_id,
        client_id=str(g.client_id),
        required_level=AccessLevel.admin.value,
    )
    item = service.upsert_company_access(str(g.client_id), company_id, user_id, access_level)
    AuditService().log_action(
        client_id=str(g.client_id),
        actor_user_id=str(g.user.id),
        action="assign_acl",
        entity_type="company",
        entity_id=company_id,
        metadata={"user_id": user_id, "access_level": access_level},
    )
    db.session.commit()
    return ok(item)


@bp.delete("/admin/companies/<company_id>/access/<user_id>")
@auth_required
@tenant_context_required
def delete_company_access(company_id: str, user_id: str):
    _require_any_permission("acl.manage")
    service = TenantAdminService()
    CompanyAccessService(service.access_repository).require_access(
        user_id=str(g.user.id),
        company_id=company_id,
        client_id=str(g.client_id),
        required_level=AccessLevel.admin.value,
    )
    service.remove_company_access(str(g.client_id), company_id, user_id)
    AuditService().log_action(
        client_id=str(g.client_id),
        actor_user_id=str(g.user.id),
        action="revoke_acl",
        entity_type="company",
        entity_id=company_id,
        metadata={"user_id": user_id},
    )
    db.session.commit()
    return ok({"deleted": True})


@bp.get("/admin/audit")
@auth_required
@tenant_context_required
def list_audit_logs():
    _require_any_permission("tenant.user.read", "tenant.users.manage")

    logs = AuditService().list_actions(
        client_id=str(g.client_id),
        entity_type=request.args.get("entity_type"),
        entity_id=request.args.get("entity_id"),
        user_id=request.args.get("user_id"),
        limit=_safe_int_arg("limit", 50),
        offset=_safe_int_arg("offset", 0),
    )
    return ok(
        {
            "items": [
                {
                    "id": item.id,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "client_id": item.client_id,
                    "actor_user_id": item.actor_user_id,
                    "actor_email": item.actor_user.email if item.actor_user else None,
                    "action": item.action,
                    "entity_type": item.entity_type,
                    "entity_id": item.entity_id,
                    "metadata": item.metadata_json or {},
                }
                for item in logs
            ]
        }
    )
