"""Service layer for document workflows."""

from __future__ import annotations

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from app.models.case import Case
from app.models.case_event import CaseEvent
from app.models.company import Company
from app.extensions import db
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.models.employee import Employee
from app.models.person import Person
from app.modules.cases.repository import CaseEventRepository, CaseRepository
from app.modules.documents.storage import open_file, save_upload
from app.modules.audit.audit_service import AuditService
from app.repositories.document_repository import DocumentRepository
from app.services.company_access_service import CompanyAccessService

_EXTENSION_TO_MIME = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}

DOCUMENT_STATUS_VALUES = {"pending", "processed", "archived"}


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
        self.audit_service = AuditService()

    def upload_case_document(
        self,
        client_id: str,
        company_id: str,
        case_id: str,
        actor_user_id: str,
        file: FileStorage,
        doc_type: str | None = None,
        person_id: str | None = None,
        employee_id: str | None = None,
        status: str = "pending",
    ) -> Document:
        self._ensure_case_access(client_id, company_id, case_id)
        self._validate_file(file)

        resolved_person_id, _ = self._validate_and_resolve_relations(
            client_id=client_id,
            company_id=company_id,
            case_id=case_id,
            person_id=person_id,
            employee_id=employee_id,
        )

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
                person_id=resolved_person_id,
                employee_id=employee_id,
                uploaded_by_user_id=actor_user_id,
                original_filename=original_filename,
                content_type=content_type,
                storage_path=storage_path,
                size_bytes=size_bytes,
                doc_type=(doc_type or "").strip() or None,
                status=(status or "pending").strip().lower(),
            )
        )

        self._log_upload_events(
            client_id=client_id,
            actor_user_id=actor_user_id,
            document=document,
            original_filename=original_filename,
        )

        if current_app.config.get("AUTO_EXTRACTION_ENABLED", False):
            db.session.add(
                DocumentExtraction(
                    client_id=client_id,
                    document_id=document.id,
                    company_id=company_id,
                    case_id=case_id,
                    created_by_user_id=actor_user_id,
                    provider="system",
                    schema_version="v1",
                    extracted_json={},
                    status="partial",
                )
            )

        return document

    def upload_document(
        self,
        client_id: str,
        actor_user_id: str,
        file: FileStorage,
        company_id: str | None = None,
        case_id: str | None = None,
        person_id: str | None = None,
        employee_id: str | None = None,
        doc_type: str | None = None,
        status: str = "pending",
    ) -> Document:
        self._validate_file(file)
        normalized_status = (status or "pending").strip().lower()
        if normalized_status not in DOCUMENT_STATUS_VALUES:
            raise BadRequest("invalid_document_status")

        if company_id:
            self._ensure_document_access(client_id, actor_user_id, company_id, required_level="operator")

        resolved_person_id, resolved_company_id = self._validate_and_resolve_relations(
            client_id=client_id,
            company_id=company_id,
            case_id=case_id,
            person_id=person_id,
            employee_id=employee_id,
        )

        storage_path, size_bytes, content_type, original_filename = save_upload(
            file=file,
            client_id=client_id,
            company_id=resolved_company_id,
            case_id=case_id,
        )

        document = self.document_repository.add(
            Document(
                client_id=client_id,
                company_id=resolved_company_id,
                case_id=case_id,
                person_id=resolved_person_id,
                employee_id=employee_id,
                uploaded_by_user_id=actor_user_id,
                original_filename=original_filename,
                content_type=content_type,
                storage_path=storage_path,
                size_bytes=size_bytes,
                doc_type=(doc_type or "").strip() or None,
                status=normalized_status,
            )
        )

        self._log_upload_events(
            client_id=client_id,
            actor_user_id=actor_user_id,
            document=document,
            original_filename=original_filename,
        )
        return document

    def list_case_documents(
        self,
        client_id: str,
        company_id: str,
        case_id: str,
        doc_type: str | None = None,
        status: str | None = None,
        q: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
        limit: int = 20,
        offset: int = 0,
        has_extraction: bool | None = None,
        person_id: str | None = None,
        employee_id: str | None = None,
    ) -> tuple[list[Document], int]:
        self._ensure_case_access(client_id, company_id, case_id)
        return self.document_repository.list_documents(
            client_id=client_id,
            company_id=company_id,
            case_id=case_id,
            person_id=person_id,
            employee_id=employee_id,
            doc_type=doc_type,
            status=status,
            q=q,
            sort=sort,
            order=order,
            limit=limit,
            offset=offset,
            has_extraction=has_extraction,
        )

    def list_documents(
        self,
        client_id: str,
        actor_user_id: str,
        company_id: str | None = None,
        case_id: str | None = None,
        person_id: str | None = None,
        employee_id: str | None = None,
        doc_type: str | None = None,
        status: str | None = None,
        q: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
        limit: int = 20,
        offset: int = 0,
        has_extraction: bool | None = None,
    ) -> tuple[list[Document], int]:
        if company_id:
            self._ensure_document_access(client_id, actor_user_id, company_id)

        return self.document_repository.list_documents(
            client_id=client_id,
            company_id=company_id,
            case_id=case_id,
            person_id=person_id,
            employee_id=employee_id,
            doc_type=doc_type,
            status=status,
            q=q,
            sort=sort,
            order=order,
            limit=limit,
            offset=offset,
            has_extraction=has_extraction,
        )

    def update_document_status(
        self,
        client_id: str,
        document_id: str,
        actor_user_id: str,
        status: str,
    ) -> Document:
        normalized_status = (status or "").strip().lower()
        if normalized_status not in DOCUMENT_STATUS_VALUES:
            raise BadRequest("invalid_document_status")

        document = self.get_document_metadata(
            client_id=client_id,
            document_id=document_id,
            actor_user_id=actor_user_id,
            required_access_level="operator",
        )

        previous_status = document.status
        updated = self.document_repository.update_status(document=document, status=normalized_status)

        if document.company_id and document.case_id:
            self.event_repository.create(
                CaseEvent(
                    client_id=client_id,
                    company_id=document.company_id,
                    case_id=document.case_id,
                    actor_user_id=actor_user_id,
                    event_type="status_change",
                    payload={
                        "document_id": document.id,
                        "from": previous_status,
                        "to": normalized_status,
                    },
                )
            )
        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=actor_user_id,
            action="document_status_changed",
            entity_type="document",
            entity_id=document.id,
            metadata={"from": previous_status, "to": normalized_status},
        )
        return updated

    def get_document_metadata(
        self,
        client_id: str,
        document_id: str,
        actor_user_id: str,
        required_access_level: str = "viewer",
    ) -> Document:
        document = self.document_repository.get_by_id(client_id=client_id, document_id=document_id)
        if document is None:
            raise NotFound("document_not_found")

        if document.company_id:
            self._ensure_document_access(
                client_id,
                actor_user_id,
                document.company_id,
                required_level=required_access_level,
            )
        if document.case_id and document.company_id:
            self._ensure_case_access(client_id, document.company_id, document.case_id)
        return document

    def download_document(self, client_id: str, document_id: str, actor_user_id: str):
        document = self.get_document_metadata(
            client_id=client_id,
            document_id=document_id,
            actor_user_id=actor_user_id,
        )
        return document, open_file(document.storage_path)

    def _validate_and_resolve_relations(
        self,
        client_id: str,
        company_id: str | None,
        case_id: str | None,
        person_id: str | None,
        employee_id: str | None,
    ) -> tuple[str | None, str | None]:
        normalized_company_id = company_id
        normalized_person_id = person_id

        if normalized_company_id:
            company = Company.query.filter_by(id=normalized_company_id, client_id=client_id).one_or_none()
            if company is None:
                raise BadRequest("invalid_company_id")

        if case_id:
            if not normalized_company_id:
                case = Case.query.filter_by(id=case_id, client_id=client_id).one_or_none()
                if case is None:
                    raise BadRequest("invalid_case_id")
                normalized_company_id = case.company_id
            self._ensure_case_access(client_id, normalized_company_id, case_id)

        if normalized_person_id:
            person = Person.query.filter_by(id=normalized_person_id, client_id=client_id).one_or_none()
            if person is None:
                raise BadRequest("invalid_person_id")

        if employee_id:
            employee = Employee.query.filter_by(id=employee_id, client_id=client_id).one_or_none()
            if employee is None:
                raise BadRequest("invalid_employee_id")

            if normalized_company_id and employee.company_id != normalized_company_id:
                raise BadRequest("employee_company_mismatch")
            if not normalized_company_id:
                normalized_company_id = employee.company_id

            if normalized_person_id and employee.person_id and employee.person_id != normalized_person_id:
                raise BadRequest("employee_person_mismatch")

            if not normalized_person_id and employee.person_id:
                normalized_person_id = employee.person_id

        return normalized_person_id, normalized_company_id

    def _log_upload_events(
        self,
        client_id: str,
        actor_user_id: str,
        document: Document,
        original_filename: str,
    ) -> None:
        if document.company_id and document.case_id:
            self.event_repository.create(
                CaseEvent(
                    client_id=client_id,
                    company_id=document.company_id,
                    case_id=document.case_id,
                    actor_user_id=actor_user_id,
                    event_type="attachment",
                    payload={"document_id": document.id, "filename": original_filename},
                )
            )

        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=actor_user_id,
            action="document_uploaded",
            entity_type="document",
            entity_id=document.id,
            metadata={
                "case_id": document.case_id,
                "company_id": document.company_id,
                "person_id": document.person_id,
                "employee_id": document.employee_id,
                "filename": original_filename,
            },
        )

        if document.person_id:
            self.audit_service.log_action(
                client_id=client_id,
                actor_user_id=actor_user_id,
                action="document_linked_to_person",
                entity_type="document",
                entity_id=document.id,
                metadata={"person_id": document.person_id},
            )

        if document.employee_id:
            self.audit_service.log_action(
                client_id=client_id,
                actor_user_id=actor_user_id,
                action="document_linked_to_employee",
                entity_type="document",
                entity_id=document.id,
                metadata={"employee_id": document.employee_id},
            )

    def _ensure_document_access(
        self,
        client_id: str,
        actor_user_id: str,
        company_id: str,
        required_level: str = "viewer",
    ) -> None:
        try:
            self.company_access_service.require_access(
                user_id=actor_user_id,
                company_id=company_id,
                client_id=client_id,
                required_level=required_level,
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

        if size_bytes == 0:
            raise BadRequest("file_empty")

        max_size = int(current_app.config.get("MAX_CONTENT_LENGTH", 25 * 1024 * 1024))
        if size_bytes > max_size:
            raise BadRequest("file_too_large")
