"""Service layer for document extraction workflows."""

from __future__ import annotations

from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.modules.extractions.repository import DocumentExtractionRepository
from app.repositories.document_repository import DocumentRepository
from app.modules.audit.audit_service import AuditService
from app.services.company_access_service import CompanyAccessService

_VALID_EXTRACTION_STATUS = {"success", "failed", "partial"}


class DocumentExtractionService:
    """Business logic for creating and querying document extractions."""

    def __init__(
        self,
        repository: DocumentExtractionRepository | None = None,
        document_repository: DocumentRepository | None = None,
        company_access_service: CompanyAccessService | None = None,
    ) -> None:
        self.repository = repository or DocumentExtractionRepository()
        self.document_repository = document_repository or DocumentRepository()
        self.company_access_service = company_access_service or CompanyAccessService()
        self.audit_service = AuditService()

    def create_extraction(
        self,
        client_id: str,
        actor_user_id: str,
        document: Document,
        schema_version: str,
        extracted_json: dict,
        confidence: float | None = None,
        provider: str = "manual",
        model_name: str | None = None,
        status: str = "success",
        error_message: str | None = None,
    ) -> DocumentExtraction:
        self._ensure_document_belongs_to_tenant(document=document, client_id=client_id)
        normalized_schema_version = (schema_version or "").strip()
        if not normalized_schema_version:
            raise BadRequest("schema_version_required")

        if confidence is not None and not 0 <= confidence <= 1:
            raise BadRequest("confidence_out_of_range")

        normalized_status = (status or "").strip().lower()
        if normalized_status not in _VALID_EXTRACTION_STATUS:
            raise BadRequest("invalid_status")

        extraction = DocumentExtraction(
            client_id=client_id,
            document_id=document.id,
            company_id=document.company_id,
            case_id=document.case_id,
            created_by_user_id=actor_user_id,
            provider=(provider or "").strip() or None,
            model_name=(model_name or "").strip() or None,
            schema_version=normalized_schema_version,
            extracted_json=extracted_json,
            confidence=confidence,
            status=normalized_status,
            error_message=(error_message or "").strip() or None,
        )
        created = self.repository.create(extraction)
        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=actor_user_id,
            action="create_extraction",
            entity_type="extraction",
            entity_id=created.id,
            metadata={"document_id": document.id, "status": normalized_status},
        )
        return created

    def get_document_for_actor(
        self,
        client_id: str,
        document_id: str,
        actor_user_id: str,
        required_level: str,
    ) -> Document:
        document = self.document_repository.get_by_id(client_id=client_id, document_id=document_id)
        if document is None:
            raise NotFound("document_not_found")

        self._ensure_company_access(
            client_id=client_id,
            actor_user_id=actor_user_id,
            company_id=document.company_id,
            required_level=required_level,
        )
        return document

    def get_latest(self, document_id: str, client_id: str) -> DocumentExtraction | None:
        return self.repository.get_latest_by_document(document_id=document_id, client_id=client_id)

    def list_extractions(
        self,
        document_id: str,
        client_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DocumentExtraction]:
        return self.repository.list_by_document(
            document_id=document_id,
            client_id=client_id,
            limit=limit,
            offset=offset,
        )

    def get_extraction(self, extraction_id: str, client_id: str) -> DocumentExtraction:
        extraction = self.repository.get_by_id(extraction_id=extraction_id, client_id=client_id)
        if extraction is None:
            raise NotFound("extraction_not_found")
        return extraction

    @staticmethod
    def _ensure_document_belongs_to_tenant(document: Document, client_id: str) -> None:
        if document.client_id != client_id:
            raise NotFound("document_not_found")

    def _ensure_company_access(
        self,
        client_id: str,
        actor_user_id: str,
        company_id: str,
        required_level: str,
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
