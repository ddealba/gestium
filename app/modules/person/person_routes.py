"""Person API routes."""

from __future__ import annotations

from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest

from app.common.decorators import auth_required, require_permission
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.extensions import db
from app.modules.person.person_schemas import PersonCreateRequest, PersonResponseSchema, PersonUpdateRequest
from app.modules.person.person_service import PersonService

bp = Blueprint("person", __name__)


def _parse_int_arg(name: str, default: int) -> int:
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise BadRequest(f"invalid_{name}") from exc


@bp.get("/persons")
@auth_required
@tenant_required
@require_permission("person.read")
def list_persons():
    service = PersonService()
    page = _parse_int_arg("page", 1)
    limit = _parse_int_arg("limit", 20)
    search = (request.args.get("search") or "").strip()
    status = request.args.get("status")

    if search:
        items, total = service.search_persons(str(g.client_id), search=search, status=status, page=page, limit=limit)
    else:
        items, total = service.list_persons(str(g.client_id), status=status, page=page, limit=limit)

    return ok({
        "items": [PersonResponseSchema.dump(person) for person in items],
        "total": total,
        "page": max(page, 1),
        "limit": max(limit, 1),
    })


@bp.get("/persons/<person_id>")
@auth_required
@tenant_required
@require_permission("person.read")
def get_person(person_id: str):
    service = PersonService()
    person = service.get_person(str(g.client_id), person_id)
    return ok({"person": PersonResponseSchema.dump(person)})


@bp.post("/persons")
@auth_required
@tenant_required
@require_permission("person.write")
def create_person():
    payload = request.get_json(silent=True) or {}
    create_payload = PersonCreateRequest.from_dict(payload)
    service = PersonService()
    person = service.create_person(str(g.client_id), str(g.user.id), create_payload)
    db.session.commit()
    return ok({"person": PersonResponseSchema.dump(person)}, status_code=201)


@bp.put("/persons/<person_id>")
@auth_required
@tenant_required
@require_permission("person.write")
def update_person(person_id: str):
    payload = request.get_json(silent=True) or {}
    update_payload = PersonUpdateRequest.from_dict(payload)
    service = PersonService()
    person = service.update_person(str(g.client_id), str(g.user.id), person_id, update_payload)
    db.session.commit()
    return ok({"person": PersonResponseSchema.dump(person)})
