"""Routes for person requests."""

from __future__ import annotations

from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest

from app.common.decorators import auth_required, require_permission, require_user_type
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.extensions import db
from app.modules.person_request.request_schemas import (
    PersonRequestCreateRequest,
    PersonRequestResponseSchema,
    PersonRequestSubmitRequest,
    PersonRequestUpdateRequest,
)
from app.modules.person_request.request_service import PersonRequestService

bp = Blueprint("person_request", __name__)


@bp.get("/persons/<person_id>/requests")
@auth_required
@tenant_required
@require_permission("person.read")
def list_person_requests(person_id: str):
    service = PersonRequestService()
    items = service.list_person_requests(
        client_id=str(g.client_id),
        person_id=person_id,
        status=request.args.get("status"),
        request_type=request.args.get("request_type"),
    )
    return ok({"items": [PersonRequestResponseSchema.dump(item) for item in items]})


@bp.post("/persons/<person_id>/requests")
@auth_required
@tenant_required
@require_permission("person.write")
def create_person_request(person_id: str):
    payload = PersonRequestCreateRequest.from_dict(request.get_json(silent=True) or {})
    service = PersonRequestService()
    item = service.create_person_request(str(g.client_id), person_id, str(g.user.id), payload)
    db.session.commit()
    return ok({"request": PersonRequestResponseSchema.dump(item)}, status_code=201)


@bp.get("/person-requests/<request_id>")
@auth_required
@tenant_required
@require_permission("person.read")
def get_person_request(request_id: str):
    item = PersonRequestService().get_person_request(str(g.client_id), request_id)
    return ok({"request": PersonRequestResponseSchema.dump(item)})


@bp.patch("/person-requests/<request_id>")
@auth_required
@tenant_required
@require_permission("person.write")
def update_person_request(request_id: str):
    payload = PersonRequestUpdateRequest.from_dict(request.get_json(silent=True) or {})
    item = PersonRequestService().update_person_request(str(g.client_id), request_id, payload)
    db.session.commit()
    return ok({"request": PersonRequestResponseSchema.dump(item)})


@bp.post("/person-requests/<request_id>/cancel")
@auth_required
@tenant_required
@require_permission("person.write")
def cancel_person_request(request_id: str):
    item = PersonRequestService().cancel_person_request(str(g.client_id), request_id, str(g.user.id))
    db.session.commit()
    return ok({"request": PersonRequestResponseSchema.dump(item)})


@bp.post("/person-requests/<request_id>/resolve")
@auth_required
@tenant_required
@require_permission("person.write")
def resolve_person_request(request_id: str):
    raw_payload = request.get_json(silent=True) or {}
    item = PersonRequestService().resolve_person_request(
        client_id=str(g.client_id),
        request_id=request_id,
        actor_user_id=str(g.user.id),
        resolution_payload=raw_payload.get("payload") if isinstance(raw_payload.get("payload"), dict) else {},
        status=raw_payload.get("status") or "resolved",
    )
    db.session.commit()
    return ok({"request": PersonRequestResponseSchema.dump(item)})


@bp.get("/portal/api/requests")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_list_requests():
    items = PersonRequestService().portal_list_requests(g.user, str(g.client_id), status=request.args.get("status"))
    return ok([PersonRequestResponseSchema.dump(item) for item in items])


@bp.get("/portal/api/requests/<request_id>")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_get_request(request_id: str):
    item = PersonRequestService().portal_get_request(g.user, str(g.client_id), request_id)
    return ok(PersonRequestResponseSchema.dump(item))


@bp.post("/portal/api/requests/<request_id>/submit")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_submit_request(request_id: str):
    payload = PersonRequestSubmitRequest.from_dict(request.get_json(silent=True) or {})
    item = PersonRequestService().portal_submit_request(g.user, str(g.client_id), request_id, payload)
    db.session.commit()
    return ok({"request": PersonRequestResponseSchema.dump(item)})


@bp.post("/portal/api/requests/<request_id>/upload")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_upload_request(request_id: str):
    file = request.files.get("file")
    if file is None:
        raise BadRequest("file_required")
    item = PersonRequestService().portal_upload_request(g.user, str(g.client_id), request_id, file)
    db.session.commit()
    return ok({"request": PersonRequestResponseSchema.dump(item)})
