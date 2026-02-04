"""Schemas for company requests and responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from werkzeug.exceptions import BadRequest

from app.models.company import Company


def _normalize_name(value: str | None) -> str:
    if value is None:
        raise BadRequest("name_required")
    name = value.strip()
    if not name:
        raise BadRequest("name_required")
    return name


def _normalize_tax_id(value: str | None) -> str:
    if value is None:
        raise BadRequest("tax_id_required")
    tax_id = value.strip().upper()
    if not tax_id:
        raise BadRequest("tax_id_required")
    return tax_id


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


@dataclass(frozen=True)
class CompanyCreatePayload:
    """Validated payload for company creation."""

    name: str
    tax_id: str

    @classmethod
    def from_dict(cls, payload: dict) -> "CompanyCreatePayload":
        return cls(
            name=_normalize_name(payload.get("name")),
            tax_id=_normalize_tax_id(payload.get("tax_id")),
        )


@dataclass(frozen=True)
class CompanyUpdatePayload:
    """Validated payload for company updates."""

    name: str | None = None
    tax_id: str | None = None

    @classmethod
    def from_dict(cls, payload: dict) -> "CompanyUpdatePayload":
        name_raw = payload.get("name")
        tax_id_raw = payload.get("tax_id")

        name = None
        tax_id = None

        if name_raw is not None:
            name = _normalize_name(name_raw)

        if tax_id_raw is not None:
            tax_id = _normalize_tax_id(tax_id_raw)

        if name is None and tax_id is None:
            raise BadRequest("no_fields_to_update")

        return cls(name=name, tax_id=tax_id)


class CompanyResponseSchema:
    """Serializer for company responses."""

    @staticmethod
    def dump(company: Company) -> dict:
        return {
            "id": company.id,
            "name": company.name,
            "tax_id": company.tax_id,
            "status": company.status,
            "created_at": _format_datetime(company.created_at),
            "updated_at": _format_datetime(company.updated_at),
        }
