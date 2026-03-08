"""Schemas for person requests and responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from werkzeug.exceptions import BadRequest

from app.models.person import Person

VALID_STATUSES = {"draft", "pending_info", "active", "inactive"}


def _required_text(value: str | None, field: str) -> str:
    if value is None:
        raise BadRequest(f"{field}_required")
    normalized = value.strip()
    if not normalized:
        raise BadRequest(f"{field}_required")
    return normalized


def _optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_status(value: str | None, default: str | None = None) -> str:
    if value is None:
        if default is None:
            raise BadRequest("status_required")
        return default
    status = value.strip().lower()
    if status not in VALID_STATUSES:
        raise BadRequest("invalid_status")
    return status


def _parse_date(value: str | None, field: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise BadRequest(f"invalid_{field}") from exc


def _format_date(value: date | None) -> str | None:
    return value.isoformat() if value else None


def _format_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _normalize_email(value: str | None) -> str | None:
    normalized = _optional_text(value)
    if normalized is None:
        return None
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise BadRequest("invalid_email")
    return normalized.lower()


@dataclass(frozen=True)
class PersonCreateRequest:
    first_name: str
    last_name: str
    document_type: str | None
    document_number: str
    email: str | None
    phone: str | None
    birth_date: date | None
    address_line1: str | None
    address_line2: str | None
    city: str | None
    postal_code: str | None
    country: str | None
    status: str

    @classmethod
    def from_dict(cls, payload: dict) -> "PersonCreateRequest":
        return cls(
            first_name=_required_text(payload.get("first_name"), "first_name"),
            last_name=_required_text(payload.get("last_name"), "last_name"),
            document_type=_optional_text(payload.get("document_type")),
            document_number=_required_text(payload.get("document_number"), "document_number"),
            email=_normalize_email(payload.get("email")),
            phone=_optional_text(payload.get("phone")),
            birth_date=_parse_date(payload.get("birth_date"), "birth_date"),
            address_line1=_optional_text(payload.get("address_line1")),
            address_line2=_optional_text(payload.get("address_line2")),
            city=_optional_text(payload.get("city")),
            postal_code=_optional_text(payload.get("postal_code")),
            country=_optional_text(payload.get("country")),
            status=_normalize_status(payload.get("status"), default="draft"),
        )


@dataclass(frozen=True)
class PersonUpdateRequest:
    first_name: str | None = None
    last_name: str | None = None
    document_type: str | None = None
    document_number: str | None = None
    email: str | None = None
    phone: str | None = None
    birth_date: date | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    postal_code: str | None = None
    country: str | None = None
    status: str | None = None

    @classmethod
    def from_dict(cls, payload: dict) -> "PersonUpdateRequest":
        values = {
            "first_name": _required_text(payload.get("first_name"), "first_name") if "first_name" in payload else None,
            "last_name": _required_text(payload.get("last_name"), "last_name") if "last_name" in payload else None,
            "document_type": _optional_text(payload.get("document_type")) if "document_type" in payload else None,
            "document_number": _required_text(payload.get("document_number"), "document_number") if "document_number" in payload else None,
            "email": _normalize_email(payload.get("email")) if "email" in payload else None,
            "phone": _optional_text(payload.get("phone")) if "phone" in payload else None,
            "birth_date": _parse_date(payload.get("birth_date"), "birth_date") if "birth_date" in payload else None,
            "address_line1": _optional_text(payload.get("address_line1")) if "address_line1" in payload else None,
            "address_line2": _optional_text(payload.get("address_line2")) if "address_line2" in payload else None,
            "city": _optional_text(payload.get("city")) if "city" in payload else None,
            "postal_code": _optional_text(payload.get("postal_code")) if "postal_code" in payload else None,
            "country": _optional_text(payload.get("country")) if "country" in payload else None,
            "status": _normalize_status(payload.get("status")) if "status" in payload else None,
        }

        if all(value is None for value in values.values()):
            raise BadRequest("no_fields_to_update")

        return cls(**values)


class PersonResponseSchema:
    @staticmethod
    def dump(person: Person) -> dict:
        return {
            "id": person.id,
            "client_id": person.client_id,
            "first_name": person.first_name,
            "last_name": person.last_name,
            "full_name": f"{person.first_name} {person.last_name}".strip(),
            "document_type": person.document_type,
            "document_number": person.document_number,
            "email": person.email,
            "phone": person.phone,
            "birth_date": _format_date(person.birth_date),
            "address_line1": person.address_line1,
            "address_line2": person.address_line2,
            "city": person.city,
            "postal_code": person.postal_code,
            "country": person.country,
            "status": person.status,
            "created_by": person.created_by,
            "created_at": _format_datetime(person.created_at),
            "updated_at": _format_datetime(person.updated_at),
        }
