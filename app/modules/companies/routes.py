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
from app.services.case_service import CaseService
from app.services.employee_service import EmployeeService

bp = Blueprint("companies", __name__)


@bp.get("/companies")
@auth_required
@tenant_required
@require_permission("company.read")
def list_companies():
    service = CompanyService()
    companies = service.list_companies(
        client_id=str(g.client_id),
        user_id=str(g.user.id),
        status=request.args.get("status"),
        q=request.args.get("q"),
    )
    return ok({"companies": [CompanyResponseSchema.dump(company) for company in companies]})


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


@bp.post("/companies/<company_id>/employees")
@auth_required
@tenant_required
@require_permission("employee.write")
@require_company_access("operator")
def create_employee(company_id: str):
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    if not name:
        raise BadRequest("name_required")

    service = EmployeeService()
    employee = service.create_employee(str(g.client_id), company_id, name)
    db.session.commit()
    return ok({"employee": employee.as_dict()}, status_code=201)


@bp.post("/companies/<company_id>/cases")
@auth_required
@tenant_required
@require_permission("case.write")
@require_company_access("operator")
def create_case(company_id: str):
    payload = request.get_json(silent=True) or {}
    title = payload.get("title")
    if not title:
        raise BadRequest("title_required")

    service = CaseService()
    case = service.create_case(str(g.client_id), company_id, title)
    db.session.commit()
    return ok({"case": case.as_dict()}, status_code=201)
