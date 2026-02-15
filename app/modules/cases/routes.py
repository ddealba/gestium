"""Case and case-event API routes."""

from __future__ import annotations

from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest

from app.common.decorators import auth_required, require_company_access, require_permission
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.extensions import db
from app.modules.cases.schemas import (
    CaseAssignRequest,
    CaseCommentRequest,
    CaseCreateRequest,
    CaseEventResponseSchema,
    CaseResponseSchema,
    CaseStatusChangeRequest,
    CaseUpdateRequest,
)
from app.modules.cases.service import CaseService

cases_bp = Blueprint("cases", __name__)
bp = cases_bp


def _parse_int_arg(name: str, default: int) -> int:
    raw_value = request.args.get(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise BadRequest(f"invalid_{name}") from exc


@cases_bp.get("/companies/<company_id>/cases")
@auth_required
@tenant_required
@require_permission("case.read")
@require_company_access("viewer")
def list_cases(company_id: str):
    service = CaseService()
    cases = service.list_company_cases(
        client_id=str(g.client_id),
        company_id=company_id,
        user_id=str(g.user.id),
        status=request.args.get("status"),
        q=request.args.get("q"),
        limit=_parse_int_arg("limit", 50),
        offset=_parse_int_arg("offset", 0),
    )
    return ok({"cases": [CaseResponseSchema.dump(case) for case in cases]})


@cases_bp.post("/companies/<company_id>/cases")
@auth_required
@tenant_required
@require_permission("case.write")
@require_company_access("operator")
def create_case(company_id: str):
    payload = request.get_json(silent=True) or {}
    create_payload = CaseCreateRequest.from_dict(payload)

    service = CaseService()
    case = service.create_case(
        client_id=str(g.client_id),
        company_id=company_id,
        actor_user_id=str(g.user.id),
        payload={
            "type": create_payload.case_type,
            "title": create_payload.title,
            "description": create_payload.description,
            "due_date": create_payload.due_date,
            "responsible_user_id": create_payload.responsible_user_id,
        },
    )
    db.session.commit()
    return ok({"case": CaseResponseSchema.dump(case)}, status_code=201)


@cases_bp.get("/companies/<company_id>/cases/<case_id>")
@auth_required
@tenant_required
@require_permission("case.read")
@require_company_access("viewer")
def get_case(company_id: str, case_id: str):
    service = CaseService()
    case = service.get_case(str(g.client_id), company_id, case_id)
    return ok({"case": CaseResponseSchema.dump(case)})


@cases_bp.patch("/companies/<company_id>/cases/<case_id>")
@auth_required
@tenant_required
@require_permission("case.write")
@require_company_access("operator")
def update_case(company_id: str, case_id: str):
    payload = request.get_json(silent=True) or {}
    update_payload = CaseUpdateRequest.from_dict(payload)

    service = CaseService()
    update_fields: dict = {}
    if "type" in payload:
        update_fields["type"] = update_payload.case_type
    if "title" in payload:
        update_fields["title"] = update_payload.title
    if "description" in payload:
        update_fields["description"] = update_payload.description
    if "due_date" in payload:
        update_fields["due_date"] = update_payload.due_date

    case = service.update_case(
        client_id=str(g.client_id),
        company_id=company_id,
        case_id=case_id,
        payload=update_fields,
    )
    db.session.commit()
    return ok({"case": CaseResponseSchema.dump(case)})


@cases_bp.post("/companies/<company_id>/cases/<case_id>/status")
@auth_required
@tenant_required
@require_permission("case.assign")
@require_company_access("manager")
def change_case_status(company_id: str, case_id: str):
    payload = request.get_json(silent=True) or {}
    status_payload = CaseStatusChangeRequest.from_dict(payload)

    service = CaseService()
    case = service.change_status(
        client_id=str(g.client_id),
        company_id=company_id,
        case_id=case_id,
        actor_user_id=str(g.user.id),
        new_status=status_payload.status,
    )
    db.session.commit()
    return ok({"case": CaseResponseSchema.dump(case)})


@cases_bp.post("/companies/<company_id>/cases/<case_id>/assign")
@auth_required
@tenant_required
@require_permission("case.assign")
@require_company_access("manager")
def assign_case(company_id: str, case_id: str):
    payload = request.get_json(silent=True) or {}
    assign_payload = CaseAssignRequest.from_dict(payload)

    service = CaseService()
    case = service.assign_responsible(
        client_id=str(g.client_id),
        company_id=company_id,
        case_id=case_id,
        actor_user_id=str(g.user.id),
        responsible_user_id=assign_payload.responsible_user_id,
    )
    db.session.commit()
    return ok({"case": CaseResponseSchema.dump(case)})


@cases_bp.get("/companies/<company_id>/cases/<case_id>/events")
@auth_required
@tenant_required
@require_permission("case.read")
@require_company_access("viewer")
def list_case_events(company_id: str, case_id: str):
    service = CaseService()
    events = service.list_case_events(
        client_id=str(g.client_id),
        company_id=company_id,
        case_id=case_id,
        limit=_parse_int_arg("limit", 100),
        offset=_parse_int_arg("offset", 0),
    )
    return ok({"events": [CaseEventResponseSchema.dump(event) for event in events]})


@cases_bp.post("/companies/<company_id>/cases/<case_id>/events/comment")
@auth_required
@tenant_required
@require_permission("case.event.write")
@require_company_access("operator")
def add_case_comment(company_id: str, case_id: str):
    payload = request.get_json(silent=True) or {}
    comment_payload = CaseCommentRequest.from_dict(payload)

    service = CaseService()
    event = service.add_comment(
        client_id=str(g.client_id),
        company_id=company_id,
        case_id=case_id,
        actor_user_id=str(g.user.id),
        comment=comment_payload.comment,
    )
    db.session.commit()
    return ok({"event": CaseEventResponseSchema.dump(event)}, status_code=201)
