"""Schemas for document extraction endpoints."""

from __future__ import annotations

from datetime import datetime

from app.models.document_extraction import DocumentExtraction


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


class ExtractionResponseSchema:
    """Serializer for extraction responses."""

    @staticmethod
    def dump(extraction: DocumentExtraction) -> dict:
        return {
            "id": extraction.id,
            "document_id": extraction.document_id,
            "company_id": extraction.company_id,
            "case_id": extraction.case_id,
            "schema_version": extraction.schema_version,
            "extracted_json": extraction.extracted_json,
            "confidence": extraction.confidence,
            "provider": extraction.provider,
            "model_name": extraction.model_name,
            "status": extraction.status,
            "error_message": extraction.error_message,
            "created_at": _format_datetime(extraction.created_at),
            "created_by_user_id": extraction.created_by_user_id,
        }

    @classmethod
    def wrap(cls, extraction: DocumentExtraction) -> dict:
        return {"extraction": cls.dump(extraction)}


class ExtractionListResponseSchema:
    """Serializer for paginated extraction lists."""

    @staticmethod
    def dump(extractions: list[DocumentExtraction], limit: int, offset: int) -> dict:
        return {
            "items": [ExtractionResponseSchema.dump(extraction) for extraction in extractions],
            "limit": limit,
            "offset": offset,
            "count": len(extractions),
        }


class CreateExtractionRequest:
    """Parser for extraction creation payload."""

    @staticmethod
    def load(payload: dict | None) -> dict:
        data = payload or {}
        schema_version = (data.get("schema_version") or "").strip()
        if not schema_version:
            raise ValueError("schema_version_required")

        extracted_json = data.get("extracted_json")
        if not isinstance(extracted_json, dict):
            raise ValueError("extracted_json_required")

        confidence = data.get("confidence")
        if confidence is not None and not isinstance(confidence, (int, float)):
            raise ValueError("confidence_must_be_number")

        return {
            "schema_version": schema_version,
            "extracted_json": extracted_json,
            "confidence": float(confidence) if confidence is not None else None,
            "provider": data.get("provider"),
            "model_name": data.get("model_name"),
            "status": data.get("status") or "success",
            "error_message": data.get("error_message"),
        }
