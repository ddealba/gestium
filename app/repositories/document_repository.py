"""Repository for document data access."""

from __future__ import annotations

from sqlalchemy import false
from werkzeug.exceptions import BadRequest

from app.extensions import db
from app.models.document import Document


VALID_SORT_FIELDS = {"created_at", "status"}
VALID_ORDERS = {"asc", "desc"}


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

    def list_by_case(
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
    ) -> tuple[list[Document], int]:
        query = self.session.query(Document).filter(
            Document.client_id == client_id,
            Document.company_id == company_id,
            Document.case_id == case_id,
        )

        if doc_type:
            query = query.filter(Document.doc_type == doc_type)

        if status:
            query = query.filter(Document.status == status)

        if q is not None:
            q_value = q.strip()
            if q_value:
                like_query = f"%{q_value}%"
                query = query.filter(Document.original_filename.ilike(like_query))

        if sort not in VALID_SORT_FIELDS:
            raise BadRequest("invalid_sort")

        if order not in VALID_ORDERS:
            raise BadRequest("invalid_order")

        sort_column = getattr(Document, sort)
        direction = sort_column.asc() if order == "asc" else sort_column.desc()
        fallback_direction = Document.created_at.asc() if order == "asc" else Document.created_at.desc()

        total_count = query.count()
        items = (
            query.order_by(direction, fallback_direction)
            .limit(max(limit, 1))
            .offset(max(offset, 0))
            .all()
        )
        return items, total_count

    @staticmethod
    def filter_by_allowed_companies(query, allowed_company_ids: set[str]):
        if not allowed_company_ids:
            return query.filter(false())
        return query.filter(Document.company_id.in_(allowed_company_ids))
