"""Repository for document data access."""

from __future__ import annotations

from sqlalchemy import false

from app.extensions import db
from app.models.document import Document


class DocumentRepository:
    """Data access layer for Document."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def add(self, document: Document) -> Document:
        self.session.add(document)
        self.session.flush()
        return document

    def get_by_id(self, client_id: str, document_id: str) -> Document | None:
        return (
            self.session.query(Document)
            .filter(Document.id == document_id, Document.client_id == client_id)
            .one_or_none()
        )

    def list_by_case(self, client_id: str, company_id: str, case_id: str) -> list[Document]:
        return (
            self.session.query(Document)
            .filter(
                Document.client_id == client_id,
                Document.company_id == company_id,
                Document.case_id == case_id,
            )
            .order_by(Document.created_at.desc())
            .all()
        )

    @staticmethod
    def filter_by_allowed_companies(query, allowed_company_ids: set[str]):
        if not allowed_company_ids:
            return query.filter(false())
        return query.filter(Document.company_id.in_(allowed_company_ids))
