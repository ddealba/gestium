"""Schemas for document module responses."""

from __future__ import annotations

from datetime import datetime

from app.models.document import Document


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _person_full_name(document: Document) -> str | None:
    person = getattr(document, "person", None)
    if person is None:
        return None
    return f"{person.first_name} {person.last_name}".strip()


class DocumentResponseSchema:
    """Serializer for document metadata responses."""

    @staticmethod
    def dump(document: Document) -> dict:
        company = getattr(document, "company", None)
        employee = getattr(document, "employee", None)
        return {
            "id": document.id,
            "original_filename": document.original_filename,
            "status": document.status,
            "has_extraction": bool(getattr(document, "has_extraction", False)),
            "created_at": _format_datetime(document.created_at),
            "uploaded_by_user_id": document.uploaded_by_user_id,
            "doc_type": document.doc_type,
            "size_bytes": document.size_bytes,
            "company_id": document.company_id,
            "company_name": company.name if company else None,
            "case_id": document.case_id,
            "person_id": document.person_id,
            "person_full_name": _person_full_name(document),
            "employee_id": document.employee_id,
            "employee_status": employee.status if employee else None,
        }

    @classmethod
    def wrap(cls, document: Document) -> dict:
        return {"document": cls.dump(document)}


class DocumentListResponseSchema:
    """Serializer for case document list responses."""

    @staticmethod
    def dump(documents: list[Document], total: int, limit: int, offset: int) -> dict:
        return {
            "items": [DocumentResponseSchema.dump(document) for document in documents],
            "total": total,
            "limit": max(limit, 1),
            "offset": max(offset, 0),
        }


class UploadResponseSchema:
    """Serializer for upload responses."""

    @staticmethod
    def dump(document: Document) -> dict:
        return {"document": DocumentResponseSchema.dump(document)}
