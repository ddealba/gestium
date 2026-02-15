"""Schemas for case and case-event requests and responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from werkzeug.exceptions import BadRequest

from app.models.case import Case
from app.models.case_event import CaseEvent

_ALLOWED_CASE_STATUSES = {"open", "in_progress", "waiting", "done", "cancelled"}


def _normalize_required_str(value: str | None, error_code: str) -> str:
    if value is None:
        raise BadRequest(error_code)
    normalized = value.strip()
    if not normalized:
        raise BadRequest(error_code)
    return normalized


def _normalize_optional_str(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _parse_date(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise BadRequest(f"invalid_{field}") from exc


def _normalize_status(value: str | None) -> str:
    status = _normalize_required_str(value, "status_required").lower()
    if status not in _ALLOWED_CASE_STATUSES:
        raise BadRequest("invalid_status")
    return status


def _format_date(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


@dataclass(frozen=True)
class CaseCreateRequest:
    """Validated payload for case creation."""

    case_type: str
    title: str
    description: str | None = None
    due_date: date | None = None
    responsible_user_id: str | None = None

    @classmethod
    def from_dict(cls, payload: dict) -> "CaseCreateRequest":
        return cls(
            case_type=_normalize_required_str(payload.get("type"), "type_required"),
            title=_normalize_required_str(payload.get("title"), "title_required"),
            description=_normalize_optional_str(payload.get("description")),
            due_date=_parse_date(payload.get("due_date"), "due_date"),
            responsible_user_id=_normalize_optional_str(payload.get("responsible_user_id")),
        )


@dataclass(frozen=True)
class CaseUpdateRequest:
    """Validated payload for case updates."""

    case_type: str | None = None
    title: str | None = None
    description: str | None = None
    due_date: date | None = None

    @classmethod
    def from_dict(cls, payload: dict) -> "CaseUpdateRequest":
        has_type = "type" in payload
        has_title = "title" in payload
        has_description = "description" in payload
        has_due_date = "due_date" in payload

        if not any((has_type, has_title, has_description, has_due_date)):
            raise BadRequest("no_fields_to_update")

        return cls(
            case_type=(
                _normalize_required_str(payload.get("type"), "type_required") if has_type else None
            ),
            title=(
                _normalize_required_str(payload.get("title"), "title_required")
                if has_title
                else None
            ),
            description=(
                _normalize_optional_str(payload.get("description")) if has_description else None
            ),
            due_date=_parse_date(payload.get("due_date"), "due_date") if has_due_date else None,
        )


@dataclass(frozen=True)
class CaseStatusChangeRequest:
    """Validated payload for case status updates."""

    status: str

    @classmethod
    def from_dict(cls, payload: dict) -> "CaseStatusChangeRequest":
        return cls(status=_normalize_status(payload.get("status")))


@dataclass(frozen=True)
class CaseAssignRequest:
    """Validated payload for case assignment."""

    responsible_user_id: str

    @classmethod
    def from_dict(cls, payload: dict) -> "CaseAssignRequest":
        return cls(
            responsible_user_id=_normalize_required_str(
                payload.get("responsible_user_id"), "responsible_user_id_required"
            )
        )


@dataclass(frozen=True)
class CaseCommentRequest:
    """Validated payload for case comments."""

    comment: str

    @classmethod
    def from_dict(cls, payload: dict) -> "CaseCommentRequest":
        return cls(comment=_normalize_required_str(payload.get("comment"), "comment_required"))


class CaseResponseSchema:
    """Serializer for case responses."""

    @staticmethod
    def dump(case: Case) -> dict:
        return {
            "id": case.id,
            "client_id": case.client_id,
            "company_id": case.company_id,
            "type": case.type,
            "title": case.title,
            "description": case.description,
            "status": case.status,
            "responsible_user_id": case.responsible_user_id,
            "due_date": _format_date(case.due_date),
            "created_at": _format_datetime(case.created_at),
            "updated_at": _format_datetime(case.updated_at),
        }


class CaseEventResponseSchema:
    """Serializer for case event responses."""

    @staticmethod
    def dump(event: CaseEvent) -> dict:
        return {
            "id": event.id,
            "client_id": event.client_id,
            "company_id": event.company_id,
            "case_id": event.case_id,
            "actor_user_id": event.actor_user_id,
            "event_type": event.event_type,
            "payload": event.payload,
            "created_at": _format_datetime(event.created_at),
        }
