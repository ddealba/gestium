"""Schemas for document module responses."""

from __future__ import annotations

from datetime import datetime

from app.models.document import Document


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


class DocumentResponseSchema:
    """Serializer for document metadata responses."""

    @staticmethod
    def dump(document: Document) -> dict:
        return {
            "id": document.id,
            "original_filename": document.original_filename,
            "status": document.status,
            "has_extraction": bool(getattr(document, "has_extraction", False)),
            "created_at": _format_datetime(document.created_at),
            "uploaded_by_user_id": document.uploaded_by_user_id,
            "doc_type": document.doc_type,
            "size_bytes": document.size_bytes,
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
