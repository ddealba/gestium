"""Document extraction routes."""

from __future__ import annotations

from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest, NotFound

from app.common.decorators import auth_required, require_permission
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.extensions import db
from app.modules.extractions.schemas import (
    CreateExtractionRequest,
    ExtractionListResponseSchema,
    ExtractionResponseSchema,
)
from app.modules.extractions.service import DocumentExtractionService

bp = Blueprint("extractions", __name__)


@bp.post("/documents/<document_id>/extractions")
@auth_required
@tenant_required
@require_permission("document.extraction.write")
def create_extraction(document_id: str):
    service = DocumentExtractionService()
    document = service.get_document_for_actor(
        client_id=str(g.client_id),
        document_id=document_id,
        actor_user_id=str(g.user.id),
        required_level="operator",
    )

    try:
        payload = CreateExtractionRequest.load(request.get_json(silent=True))
    except ValueError as exc:
        raise BadRequest(str(exc)) from exc

    extraction = service.create_extraction(
        client_id=str(g.client_id),
        actor_user_id=str(g.user.id),
        document=document,
        **payload,
    )
    db.session.commit()
    return ok(ExtractionResponseSchema.wrap(extraction), status_code=201)


@bp.get("/documents/<document_id>/extractions/latest")
@auth_required
@tenant_required
@require_permission("document.extraction.read")
def get_latest_extraction(document_id: str):
    service = DocumentExtractionService()
    service.get_document_for_actor(
        client_id=str(g.client_id),
        document_id=document_id,
        actor_user_id=str(g.user.id),
        required_level="viewer",
    )

    extraction = service.get_latest(document_id=document_id, client_id=str(g.client_id))
    if extraction is None:
        raise NotFound("extraction_not_found")
    return ok(ExtractionResponseSchema.wrap(extraction))


@bp.get("/documents/<document_id>/extractions")
@auth_required
@tenant_required
@require_permission("document.extraction.read")
def list_extractions(document_id: str):
    service = DocumentExtractionService()
    service.get_document_for_actor(
        client_id=str(g.client_id),
        document_id=document_id,
        actor_user_id=str(g.user.id),
        required_level="viewer",
    )

    try:
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
    except ValueError as exc:
        raise BadRequest("invalid_pagination") from exc

    if limit < 1 or offset < 0:
        raise BadRequest("invalid_pagination")

    extractions = service.list_extractions(
        document_id=document_id,
        client_id=str(g.client_id),
        limit=limit,
        offset=offset,
    )
    return ok(ExtractionListResponseSchema.dump(extractions, limit=limit, offset=offset))
