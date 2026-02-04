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

    @staticmethod
    def filter_by_allowed_companies(query, allowed_company_ids: set[str]):
        if not allowed_company_ids:
            return query.filter(false())
        return query.filter(Document.company_id.in_(allowed_company_ids))
