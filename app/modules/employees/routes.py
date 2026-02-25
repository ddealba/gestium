"""Employee routes."""

from __future__ import annotations

from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest

from app.common.decorators import auth_required, require_company_access, require_permission
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.extensions import db
from app.modules.employees.schemas import (
    EmployeeCreateRequest,
    EmployeeResponseSchema,
    EmployeeTerminateRequest,
    EmployeeUpdateRequest,
)
from app.modules.employees.service import EmployeeService

bp = Blueprint("employees", __name__)


def _parse_int_arg(name: str, default: int) -> int:
    raw_value = request.args.get(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise BadRequest(f"invalid_{name}") from exc


@bp.get("/companies/<company_id>/employees")
@auth_required
@tenant_required
@require_permission("employee.read")
@require_company_access("viewer")
def list_employees(company_id: str):
    service = EmployeeService()
    limit = _parse_int_arg("limit", 20)
    offset = _parse_int_arg("offset", 0)
    employees, total = service.list_employees(
        str(g.client_id),
        company_id,
        q=request.args.get("q"),
        status=request.args.get("status"),
        sort=request.args.get("sort") or "name",
        order=request.args.get("order") or "asc",
        limit=limit,
        offset=offset,
    )
    return ok({
        "items": [EmployeeResponseSchema.dump(employee) for employee in employees],
        "total": total,
        "limit": max(limit, 1),
        "offset": max(offset, 0),
    })


@bp.post("/companies/<company_id>/employees")
@auth_required
@tenant_required
@require_permission("employee.write")
@require_company_access("operator")
def create_employee(company_id: str):
    payload = request.get_json(silent=True) or {}
    create_payload = EmployeeCreateRequest.from_dict(payload)
    service = EmployeeService()
    employee = service.create_employee(str(g.client_id), company_id, create_payload)
    db.session.commit()
    return ok({"employee": EmployeeResponseSchema.dump(employee)}, status_code=201)


@bp.get("/companies/<company_id>/employees/<employee_id>")
@auth_required
@tenant_required
@require_permission("employee.read")
@require_company_access("viewer")
def get_employee(company_id: str, employee_id: str):
    service = EmployeeService()
    employee = service.get_employee(str(g.client_id), company_id, employee_id)
    return ok({"employee": EmployeeResponseSchema.dump(employee)})


@bp.patch("/companies/<company_id>/employees/<employee_id>")
@auth_required
@tenant_required
@require_permission("employee.write")
@require_company_access("operator")
def update_employee(company_id: str, employee_id: str):
    payload = request.get_json(silent=True) or {}
    update_payload = EmployeeUpdateRequest.from_dict(payload)
    service = EmployeeService()
    employee = service.update_employee(str(g.client_id), company_id, employee_id, update_payload)
    db.session.commit()
    return ok({"employee": EmployeeResponseSchema.dump(employee)})


@bp.post("/companies/<company_id>/employees/<employee_id>/terminate")
@auth_required
@tenant_required
@require_permission("employee.write")
@require_company_access("manager")
def terminate_employee(company_id: str, employee_id: str):
    payload = request.get_json(silent=True) or {}
    terminate_payload = EmployeeTerminateRequest.from_dict(payload)
    service = EmployeeService()
    employee = service.terminate_employee(str(g.client_id), company_id, employee_id, terminate_payload)
    db.session.commit()
    return ok({"employee": EmployeeResponseSchema.dump(employee)})
