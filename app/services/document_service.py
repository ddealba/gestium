"""Service layer for document operations."""

from __future__ import annotations

from app.models.document import Document
from app.repositories.document_repository import DocumentRepository


class DocumentService:
    """Document service for CRUD operations."""

    def __init__(self, repository: DocumentRepository | None = None) -> None:
        self.repository = repository or DocumentRepository()

    def create_document(
        self,
        client_id: str,
        original_filename: str,
        storage_path: str,
        company_id: str | None = None,
        case_id: str | None = None,
        person_id: str | None = None,
        employee_id: str | None = None,
        uploaded_by_user_id: str | None = None,
        content_type: str | None = None,
        size_bytes: int | None = None,
        doc_type: str | None = None,
        status: str = "pending",
    ) -> Document:
        document = Document(
            client_id=client_id,
            company_id=company_id,
            case_id=case_id,
            person_id=person_id,
            employee_id=employee_id,
            uploaded_by_user_id=uploaded_by_user_id,
            original_filename=original_filename,
            content_type=content_type,
            storage_path=storage_path,
            size_bytes=size_bytes,
            doc_type=doc_type,
            status=status,
        )
        return self.repository.add(document)

    def upload_document(self, *args, **kwargs) -> Document:
        return self.create_document(*args, **kwargs)
