"""Document routes."""

from __future__ import annotations

from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest

from app.common.decorators import auth_required, require_company_access, require_permission
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.extensions import db
from app.services.document_service import DocumentService

bp = Blueprint("documents", __name__)


@bp.post("/documents/upload")
@auth_required
@tenant_required
@require_permission("document.upload")
@require_company_access("operator", company_id_arg="company_id")
def upload_document():
    payload = request.get_json(silent=True) or {}
    company_id = payload.get("company_id")
    filename = payload.get("filename")
    if not company_id:
        raise BadRequest("company_id_required")
    if not filename:
        raise BadRequest("filename_required")

    service = DocumentService()
    document = service.upload_document(str(g.client_id), str(company_id), filename)
    db.session.commit()
    return ok({"document": document.as_dict()}, status_code=201)
