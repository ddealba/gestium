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
    case_id = payload.get("case_id")
    original_filename = payload.get("original_filename") or payload.get("filename")
    if not company_id:
        raise BadRequest("company_id_required")
    if not case_id:
        raise BadRequest("case_id_required")
    if not original_filename:
        raise BadRequest("original_filename_required")

    storage_path = payload.get("storage_path") or f"documents/{g.client_id}/{company_id}/{case_id}/{original_filename}"

    service = DocumentService()
    document = service.upload_document(
        client_id=str(g.client_id),
        company_id=str(company_id),
        case_id=str(case_id),
        uploaded_by_user_id=str(g.user.id),
        original_filename=original_filename,
        content_type=payload.get("content_type"),
        storage_path=storage_path,
        size_bytes=payload.get("size_bytes"),
        doc_type=payload.get("doc_type"),
        status=payload.get("status") or "pending",
    )
    db.session.commit()
    return ok({"document": document.as_dict()}, status_code=201)
