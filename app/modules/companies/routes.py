"""Company and related resource routes."""

from __future__ import annotations

from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest

from app.common.decorators import auth_required, require_company_access, require_permission
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.extensions import db
from app.services.case_service import CaseService
from app.services.company_service import CompanyService
from app.services.employee_service import EmployeeService

bp = Blueprint("companies", __name__)


@bp.get("/companies")
@auth_required
@tenant_required
@require_permission("company.read")
def list_companies():
    service = CompanyService()
    companies = service.list_companies(str(g.user.id), str(g.client_id))
    return ok({"companies": [company.as_dict() for company in companies]})


@bp.get("/companies/<company_id>")
@auth_required
@tenant_required
@require_permission("company.read")
@require_company_access("viewer")
def get_company(company_id: str):
    service = CompanyService()
    company = service.get_company(company_id, str(g.client_id))
    return ok({"company": company.as_dict()})


@bp.patch("/companies/<company_id>")
@auth_required
@tenant_required
@require_permission("company.write")
@require_company_access("operator")
def update_company(company_id: str):
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    if not name:
        raise BadRequest("name_required")

    service = CompanyService()
    company = service.get_company(company_id, str(g.client_id))
    company = service.update_company_name(company, name)
    db.session.commit()
    return ok({"company": company.as_dict()})


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
