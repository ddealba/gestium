"""Schemas for person-company relations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from werkzeug.exceptions import BadRequest

from app.models.person_company_relation import PersonCompanyRelation

VALID_RELATION_TYPES = {"owner", "employee", "other"}
VALID_STATUSES = {"active", "inactive"}


def _parse_date(value: str | None, field: str, required: bool = False) -> date | None:
    if value is None:
        if required:
            raise BadRequest(f"{field}_required")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise BadRequest(f"invalid_{field}") from exc


def _normalize_relation_type(value: str | None) -> str:
    if value is None:
        raise BadRequest("relation_type_required")
    normalized = value.strip().lower()
    if normalized not in VALID_RELATION_TYPES:
        raise BadRequest("invalid_relation_type")
    return normalized


def _normalize_status(value: str | None, default: str = "active") -> str:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized not in VALID_STATUSES:
        raise BadRequest("invalid_status")
    return normalized


def _optional_notes(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _format_date(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _format_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@dataclass(frozen=True)
class PersonCompanyRelationCreateRequest:
    company_id: str
    relation_type: str
    status: str
    start_date: date
    end_date: date | None
    notes: str | None

    @classmethod
    def from_dict(cls, payload: dict) -> "PersonCompanyRelationCreateRequest":
        company_id = (payload.get("company_id") or "").strip()
        if not company_id:
            raise BadRequest("company_id_required")
        return cls(
            company_id=company_id,
            relation_type=_normalize_relation_type(payload.get("relation_type")),
            status=_normalize_status(payload.get("status"), default="active"),
            start_date=_parse_date(payload.get("start_date"), "start_date", required=True),
            end_date=_parse_date(payload.get("end_date"), "end_date"),
            notes=_optional_notes(payload.get("notes")),
        )


@dataclass(frozen=True)
class PersonCompanyRelationUpdateRequest:
    relation_type: str | None = None
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    notes: str | None = None

    @classmethod
    def from_dict(cls, payload: dict) -> "PersonCompanyRelationUpdateRequest":
        values = {
            "relation_type": _normalize_relation_type(payload.get("relation_type")) if "relation_type" in payload else None,
            "status": _normalize_status(payload.get("status"), default="active") if "status" in payload else None,
            "start_date": _parse_date(payload.get("start_date"), "start_date") if "start_date" in payload else None,
            "end_date": _parse_date(payload.get("end_date"), "end_date") if "end_date" in payload else None,
            "notes": _optional_notes(payload.get("notes")) if "notes" in payload else None,
        }
        if all(value is None for value in values.values()):
            raise BadRequest("no_fields_to_update")
        return cls(**values)


class PersonCompanyRelationResponseSchema:
    @staticmethod
    def dump(relation: PersonCompanyRelation) -> dict:
        return {
            "id": relation.id,
            "client_id": relation.client_id,
            "person_id": relation.person_id,
            "company_id": relation.company_id,
            "relation_type": relation.relation_type,
            "status": relation.status,
            "start_date": _format_date(relation.start_date),
            "end_date": _format_date(relation.end_date),
            "notes": relation.notes,
            "created_by": relation.created_by,
            "created_at": _format_datetime(relation.created_at),
            "updated_at": _format_datetime(relation.updated_at),
        }
