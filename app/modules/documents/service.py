"""Service layer for document workflows."""

from __future__ import annotations

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from app.models.case_event import CaseEvent
from app.models.document import Document
from app.modules.cases.repository import CaseEventRepository, CaseRepository
from app.modules.documents.storage import open_file, save_upload
from app.repositories.document_repository import DocumentRepository
from app.services.company_access_service import CompanyAccessService

_EXTENSION_TO_MIME = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


class DocumentModuleService:
    """Business logic for document uploads and retrieval."""

    def __init__(
        self,
        document_repository: DocumentRepository | None = None,
        case_repository: CaseRepository | None = None,
        event_repository: CaseEventRepository | None = None,
        company_access_service: CompanyAccessService | None = None,
    ) -> None:
        self.document_repository = document_repository or DocumentRepository()
        self.case_repository = case_repository or CaseRepository()
        self.event_repository = event_repository or CaseEventRepository()
        self.company_access_service = company_access_service or CompanyAccessService()

    def upload_case_document(
        self,
        client_id: str,
        company_id: str,
        case_id: str,
        actor_user_id: str,
        file: FileStorage,
        doc_type: str | None = None,
    ) -> Document:
        self._ensure_case_access(client_id, company_id, case_id)
        self._validate_file(file)

        storage_path, size_bytes, content_type, original_filename = save_upload(
            file=file,
            client_id=client_id,
            company_id=company_id,
            case_id=case_id,
        )

        document = self.document_repository.add(
            Document(
                client_id=client_id,
                company_id=company_id,
                case_id=case_id,
                uploaded_by_user_id=actor_user_id,
                original_filename=original_filename,
                content_type=content_type,
                storage_path=storage_path,
                size_bytes=size_bytes,
                doc_type=(doc_type or "").strip() or None,
                status="pending",
            )
        )

        self.event_repository.create(
            CaseEvent(
                client_id=client_id,
                company_id=company_id,
                case_id=case_id,
                actor_user_id=actor_user_id,
                event_type="attachment",
                payload={"document_id": document.id, "filename": original_filename},
            )
        )

        return document

    def list_case_documents(self, client_id: str, company_id: str, case_id: str) -> list[Document]:
        self._ensure_case_access(client_id, company_id, case_id)
        return self.document_repository.list_by_case(client_id=client_id, company_id=company_id, case_id=case_id)

    def get_document_metadata(self, client_id: str, document_id: str, actor_user_id: str) -> Document:
        document = self.document_repository.get_by_id(client_id=client_id, document_id=document_id)
        if document is None:
            raise NotFound("document_not_found")
        self._ensure_document_access(client_id, actor_user_id, document.company_id)
        self._ensure_case_access(client_id, document.company_id, document.case_id)
        return document

    def download_document(self, client_id: str, document_id: str, actor_user_id: str):
        document = self.get_document_metadata(
            client_id=client_id,
            document_id=document_id,
            actor_user_id=actor_user_id,
        )
        return document, open_file(document.storage_path)

    def _ensure_document_access(self, client_id: str, actor_user_id: str, company_id: str) -> None:
        try:
            self.company_access_service.require_access(
                user_id=actor_user_id,
                company_id=company_id,
                client_id=client_id,
                required_level="viewer",
            )
        except (Forbidden, NotFound) as exc:
            raise NotFound("document_not_found") from exc

    def _ensure_case_access(self, client_id: str, company_id: str, case_id: str) -> None:
        case = self.case_repository.get_by_id(case_id=case_id, client_id=client_id)
        if case is None or case.company_id != company_id:
            raise NotFound("case_not_found")

    def _validate_file(self, file: FileStorage | None) -> None:
        if file is None or not file.filename:
            raise BadRequest("file_required")

        filename = file.filename.rsplit(".", 1)
        if len(filename) != 2:
            raise BadRequest("invalid_file_extension")

        extension = filename[1].lower()
        content_type = (file.mimetype or "").lower()
        allowed_values = {value.lower() for value in current_app.config.get("ALLOWED_DOCUMENT_MIME", ())}

        normalized_allowed_extensions = set()
        normalized_allowed_mimes = set()
        for value in allowed_values:
            if "/" in value:
                normalized_allowed_mimes.add(value)
            else:
                normalized_allowed_extensions.add(value)
                mapped_mime = _EXTENSION_TO_MIME.get(value)
                if mapped_mime:
                    normalized_allowed_mimes.add(mapped_mime)

        if extension not in normalized_allowed_extensions:
            raise BadRequest("extension_not_allowed")
        if content_type and content_type not in normalized_allowed_mimes:
            raise BadRequest("mimetype_not_allowed")

        file.stream.seek(0, 2)
        size_bytes = file.stream.tell()
        file.stream.seek(0)

        max_size = int(current_app.config.get("MAX_CONTENT_LENGTH", 25 * 1024 * 1024))
        if size_bytes > max_size:
            raise BadRequest("file_too_large")
