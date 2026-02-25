"""Company and related resource routes."""

from __future__ import annotations

from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest
from app.common.decorators import auth_required, require_company_access, require_permission
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.extensions import db
from app.modules.companies.schemas import (
    CompanyCreatePayload,
    CompanyResponseSchema,
    CompanyUpdatePayload,
)
from app.modules.companies.service import CompanyService

bp = Blueprint("companies", __name__)


def _parse_int_arg(name: str, default: int) -> int:
    raw_value = request.args.get(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise BadRequest(f"invalid_{name}") from exc


@bp.get("/companies")
@auth_required
@tenant_required
@require_permission("company.read")
def list_companies():
    service = CompanyService()
    limit = _parse_int_arg("limit", 20)
    offset = _parse_int_arg("offset", 0)
    companies, total = service.list_companies(
        client_id=str(g.client_id),
        user_id=str(g.user.id),
        status=request.args.get("status"),
        q=request.args.get("q"),
        sort=request.args.get("sort") or "created_at",
        order=request.args.get("order") or "desc",
        limit=limit,
        offset=offset,
    )
    return ok({
        "items": [CompanyResponseSchema.dump(company) for company in companies],
        "total": total,
        "limit": max(limit, 1),
        "offset": max(offset, 0),
    })


@bp.post("/companies")
@auth_required
@tenant_required
@require_permission("company.write")
def create_company():
    payload = request.get_json(silent=True) or {}
    company_payload = CompanyCreatePayload.from_dict(payload)
    service = CompanyService()
    company = service.create_company(
        client_id=str(g.client_id),
        user_id=str(g.user.id),
        payload=company_payload,
    )
    db.session.commit()
    return ok({"company": CompanyResponseSchema.dump(company)}, status_code=201)


@bp.get("/companies/<company_id>")
@auth_required
@tenant_required
@require_permission("company.read")
@require_company_access("viewer")
def get_company(company_id: str):
    service = CompanyService()
    company = service.get_company(str(g.client_id), company_id)
    return ok({"company": CompanyResponseSchema.dump(company)})


@bp.patch("/companies/<company_id>")
@auth_required
@tenant_required
@require_permission("company.write")
@require_company_access("manager")
def update_company(company_id: str):
    payload = request.get_json(silent=True) or {}
    update_payload = CompanyUpdatePayload.from_dict(payload)
    service = CompanyService()
    company = service.update_company(
        client_id=str(g.client_id),
        company_id=company_id,
        payload=update_payload,
    )
    db.session.commit()
    return ok({"company": CompanyResponseSchema.dump(company)})


@bp.post("/companies/<company_id>/deactivate")
@auth_required
@tenant_required
@require_permission("company.write")
@require_company_access("admin")
def deactivate_company(company_id: str):
    service = CompanyService()
    company = service.deactivate_company(str(g.client_id), company_id)
    db.session.commit()
    return ok({"company": CompanyResponseSchema.dump(company)})


@bp.post("/companies/<company_id>/activate")
@auth_required
@tenant_required
@require_permission("company.write")
@require_company_access("admin")
def activate_company(company_id: str):
    service = CompanyService()
    company = service.activate_company(str(g.client_id), company_id)
    db.session.commit()
    return ok({"company": CompanyResponseSchema.dump(company)})

