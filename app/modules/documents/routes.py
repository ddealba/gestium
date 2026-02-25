"""Document routes."""

from __future__ import annotations

from flask import Blueprint, g, request, send_file
from werkzeug.exceptions import BadRequest

from app.common.decorators import auth_required, require_company_access, require_permission
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.extensions import db
from app.modules.documents.schemas import DocumentListResponseSchema, DocumentResponseSchema, UploadResponseSchema
from app.modules.documents.service import DocumentModuleService

bp = Blueprint("documents", __name__)


def _parse_int_arg(name: str, default: int) -> int:
    raw_value = request.args.get(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise BadRequest(f"invalid_{name}") from exc


def _parse_optional_bool_arg(name: str) -> bool | None:
    raw_value = request.args.get(name)
    if raw_value is None:
        return None
    normalized = raw_value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    raise BadRequest(f"invalid_{name}")


@bp.post("/companies/<company_id>/cases/<case_id>/documents")
@auth_required
@tenant_required
@require_permission("document.upload")
@require_company_access("operator", company_id_arg="company_id")
def upload_document(company_id: str, case_id: str):
    doc_type = request.form.get("doc_type")
    file = request.files.get("file")

    if file is None:
        raise BadRequest("file_required")

    service = DocumentModuleService()
    document = service.upload_case_document(
        client_id=str(g.client_id),
        company_id=company_id,
        case_id=case_id,
        actor_user_id=str(g.user.id),
        file=file,
        doc_type=doc_type,
    )
    db.session.commit()
    return ok(UploadResponseSchema.dump(document), status_code=201)


@bp.get("/companies/<company_id>/cases/<case_id>/documents")
@auth_required
@tenant_required
@require_permission("document.read")
@require_company_access("viewer", company_id_arg="company_id")
def list_case_documents(company_id: str, case_id: str):
    service = DocumentModuleService()
    limit = _parse_int_arg("limit", 20)
    offset = _parse_int_arg("offset", 0)
    documents, total = service.list_case_documents(
        client_id=str(g.client_id),
        company_id=company_id,
        case_id=case_id,
        doc_type=request.args.get("doc_type"),
        status=request.args.get("status"),
        q=request.args.get("q"),
        sort=request.args.get("sort") or "created_at",
        order=request.args.get("order") or "desc",
        limit=limit,
        offset=offset,
        has_extraction=_parse_optional_bool_arg("has_extraction"),
    )
    return ok(DocumentListResponseSchema.dump(documents, total=total, limit=limit, offset=offset))


@bp.patch("/documents/<document_id>/status")
@auth_required
@tenant_required
@require_permission("document.write")
def update_document_status(document_id: str):
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    if status is None:
        raise BadRequest("status_required")

    service = DocumentModuleService()
    document = service.update_document_status(
        client_id=str(g.client_id),
        document_id=document_id,
        actor_user_id=str(g.user.id),
        status=status,
    )
    db.session.commit()
    return ok(DocumentResponseSchema.wrap(document))


@bp.get("/documents/<document_id>/download")
@auth_required
@tenant_required
@require_permission("document.read")
def download_document(document_id: str):
    service = DocumentModuleService()
    document, (path, _) = service.download_document(
        client_id=str(g.client_id),
        document_id=document_id,
        actor_user_id=str(g.user.id),
    )
    return send_file(
        path,
        mimetype=document.content_type,
        as_attachment=True,
        download_name=document.original_filename,
    )


@bp.get("/documents/<document_id>")
@auth_required
@tenant_required
@require_permission("document.read")
def get_document_metadata(document_id: str):
    service = DocumentModuleService()
    document = service.get_document_metadata(
        client_id=str(g.client_id),
        document_id=document_id,
        actor_user_id=str(g.user.id),
    )
    return ok(DocumentResponseSchema.wrap(document))
