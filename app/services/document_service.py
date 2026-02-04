"""Service layer for document operations."""

from __future__ import annotations

from app.models.document import Document
from app.repositories.document_repository import DocumentRepository


class DocumentService:
    """Document service for CRUD operations."""

    def __init__(self, repository: DocumentRepository | None = None) -> None:
        self.repository = repository or DocumentRepository()

    def upload_document(self, client_id: str, company_id: str, filename: str) -> Document:
        document = Document(client_id=client_id, company_id=company_id, filename=filename)
        return self.repository.add(document)
