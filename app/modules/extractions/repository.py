"""Repository for document extraction data access."""

from __future__ import annotations

from app.extensions import db
from app.models.document_extraction import DocumentExtraction


class DocumentExtractionRepository:
    """Data access layer for ``DocumentExtraction``."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def create(self, extraction: DocumentExtraction) -> DocumentExtraction:
        self.session.add(extraction)
        self.session.flush()
        return extraction

    def list_by_document(
        self,
        document_id: str,
        client_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DocumentExtraction]:
        return (
            self.session.query(DocumentExtraction)
            .filter(
                DocumentExtraction.document_id == document_id,
                DocumentExtraction.client_id == client_id,
            )
            .order_by(DocumentExtraction.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def get_latest_by_document(self, document_id: str, client_id: str) -> DocumentExtraction | None:
        return (
            self.session.query(DocumentExtraction)
            .filter(
                DocumentExtraction.document_id == document_id,
                DocumentExtraction.client_id == client_id,
            )
            .order_by(DocumentExtraction.created_at.desc())
            .first()
        )

    def get_by_id(self, extraction_id: str, client_id: str) -> DocumentExtraction | None:
        return (
            self.session.query(DocumentExtraction)
            .filter(
                DocumentExtraction.id == extraction_id,
                DocumentExtraction.client_id == client_id,
            )
            .one_or_none()
        )
