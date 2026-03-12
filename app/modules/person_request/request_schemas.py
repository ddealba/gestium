"""Schemas for person request module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from werkzeug.exceptions import BadRequest

from app.models.person_request import PersonRequest

REQUEST_TYPES = {"complete_profile", "upload_document", "confirm_information", "provide_data", "other"}
REQUEST_STATUSES = {"pending", "submitted", "in_review", "resolved", "rejected", "cancelled", "expired"}
RESOLUTION_TYPES = {"manual_review", "document_upload", "form_submission", "auto_resolved", "confirm_information"}


def _required_text(value: str | None, field: str) -> str:
    if value is None:
        raise BadRequest(f"{field}_required")
    text = value.strip()
    if not text:
        raise BadRequest(f"{field}_required")
    return text


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    return text or None


def _parse_date(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise BadRequest(f"invalid_{field}") from exc


def _normalize_choice(value: str | None, field: str, valid: set[str], default: str | None = None) -> str:
    if value is None:
        if default is None:
            raise BadRequest(f"{field}_required")
        return default
    normalized = value.strip().lower()
    if normalized not in valid:
        raise BadRequest(f"invalid_{field}")
    return normalized


def _format_date(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _format_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@dataclass(frozen=True)
class PersonRequestCreateRequest:
    request_type: str
    title: str
    description: str | None
    due_date: date | None
    resolution_type: str
    company_id: str | None
    case_id: str | None
    employee_id: str | None

    @classmethod
    def from_dict(cls, payload: dict) -> "PersonRequestCreateRequest":
        return cls(
            request_type=_normalize_choice(payload.get("request_type"), "request_type", REQUEST_TYPES),
            title=_required_text(payload.get("title"), "title"),
            description=_optional_text(payload.get("description")),
            due_date=_parse_date(payload.get("due_date"), "due_date"),
            resolution_type=_normalize_choice(payload.get("resolution_type"), "resolution_type", RESOLUTION_TYPES, default="manual_review"),
            company_id=_optional_text(payload.get("company_id")),
            case_id=_optional_text(payload.get("case_id")),
            employee_id=_optional_text(payload.get("employee_id")),
        )


@dataclass(frozen=True)
class PersonRequestUpdateRequest:
    title: str | None = None
    description: str | None = None
    status: str | None = None
    due_date: date | None = None
    resolution_type: str | None = None

    @classmethod
    def from_dict(cls, payload: dict) -> "PersonRequestUpdateRequest":
        values = {
            "title": _required_text(payload.get("title"), "title") if "title" in payload else None,
            "description": _optional_text(payload.get("description")) if "description" in payload else None,
            "status": _normalize_choice(payload.get("status"), "status", REQUEST_STATUSES) if "status" in payload else None,
            "due_date": _parse_date(payload.get("due_date"), "due_date") if "due_date" in payload else None,
            "resolution_type": _normalize_choice(payload.get("resolution_type"), "resolution_type", RESOLUTION_TYPES) if "resolution_type" in payload else None,
        }
        if all(value is None for value in values.values()):
            raise BadRequest("no_fields_to_update")
        return cls(**values)




@dataclass(frozen=True)
class PersonRequestReviewRequest:
    review_notes: str | None = None

    @classmethod
    def from_dict(cls, payload: dict) -> "PersonRequestReviewRequest":
        return cls(review_notes=_optional_text(payload.get("review_notes")))


@dataclass(frozen=True)
class PersonRequestRejectRequest:
    rejection_reason: str
    review_notes: str | None = None

    @classmethod
    def from_dict(cls, payload: dict) -> "PersonRequestRejectRequest":
        return cls(
            rejection_reason=_required_text(payload.get("rejection_reason"), "rejection_reason"),
            review_notes=_optional_text(payload.get("review_notes")),
        )


@dataclass(frozen=True)
class PersonRequestSubmitRequest:
    payload: dict

    @classmethod
    def from_dict(cls, payload: dict) -> "PersonRequestSubmitRequest":
        resolved = payload.get("payload")
        if not isinstance(resolved, dict):
            raise BadRequest("payload_required")
        return cls(payload=resolved)


class PersonRequestResponseSchema:
    @staticmethod
    def dump(item: PersonRequest) -> dict:
        return {
            "id": item.id,
            "client_id": item.client_id,
            "person_id": item.person_id,
            "company_id": item.company_id,
            "case_id": item.case_id,
            "employee_id": item.employee_id,
            "request_type": item.request_type,
            "title": item.title,
            "description": item.description,
            "status": item.status,
            "due_date": _format_date(item.due_date),
            "resolution_type": item.resolution_type,
            "resolution_payload": item.resolution_payload,
            "review_notes": item.review_notes,
            "rejection_reason": item.rejection_reason,
            "submitted_at": _format_datetime(item.submitted_at),
            "reviewed_at": _format_datetime(item.reviewed_at),
            "created_by": item.created_by,
            "resolved_by": item.resolved_by,
            "created_at": _format_datetime(item.created_at),
            "updated_at": _format_datetime(item.updated_at),
            "resolved_at": _format_datetime(item.resolved_at),
        }
