"""Service layer for document extraction workflows."""

from __future__ import annotations

from werkzeug.exceptions import BadRequest, NotFound

from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.modules.extractions.repository import DocumentExtractionRepository


class DocumentExtractionService:
    """Business logic for creating and querying document extractions."""

    def __init__(self, repository: DocumentExtractionRepository | None = None) -> None:
        self.repository = repository or DocumentExtractionRepository()

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
            status=status,
            error_message=(error_message or "").strip() or None,
        )
        return self.repository.create(extraction)

    def get_latest(self, document_id: str, client_id: str) -> DocumentExtraction | None:
        return self.repository.get_latest_by_document(document_id=document_id, client_id=client_id)

    def list_extractions(self, document_id: str, client_id: str) -> list[DocumentExtraction]:
        return self.repository.list_by_document(document_id=document_id, client_id=client_id)

    def get_extraction(self, extraction_id: str, client_id: str) -> DocumentExtraction:
        extraction = self.repository.get_by_id(extraction_id=extraction_id, client_id=client_id)
        if extraction is None:
            raise NotFound("extraction_not_found")
        return extraction

    @staticmethod
    def _ensure_document_belongs_to_tenant(document: Document, client_id: str) -> None:
        if document.client_id != client_id:
            raise NotFound("document_not_found")
