"""Schemas for employee requests and responses."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from werkzeug.exceptions import BadRequest

from app.models.employee import Employee


def _normalize_full_name(value: str | None) -> str:
    if value is None:
        raise BadRequest("full_name_required")
    name = value.strip()
    if not name:
        raise BadRequest("full_name_required")
    return name


def _normalize_employee_ref(value: str | None) -> str | None:
    if value is None:
        return None
    ref = value.strip()
    return ref or None


def _normalize_status(value: str | None, *, default: str | None = None) -> str:
    if value is None:
        if default is None:
            raise BadRequest("status_required")
        return default
    status = value.strip().lower()
    if status not in {"active", "terminated"}:
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
    if value is None:
        return None
    return value.isoformat()


def _format_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def validate_status_dates(status: str, start_date: date, end_date: date | None) -> None:
    if status == "terminated":
        if end_date is None:
            raise BadRequest("end_date_required")
        if end_date < start_date:
            raise BadRequest("end_date_before_start_date")
    elif end_date is not None:
        raise BadRequest("end_date_not_allowed")


@dataclass(frozen=True)
class EmployeeCreateRequest:
    """Validated payload for employee creation."""

    full_name: str
    employee_ref: str | None
    status: str
    start_date: date
    end_date: date | None

    @classmethod
    def from_dict(cls, payload: dict) -> "EmployeeCreateRequest":
        start_date = _parse_date(payload.get("start_date"), "start_date")
        if start_date is None:
            raise BadRequest("start_date_required")

        status = _normalize_status(payload.get("status"), default="active")
        end_date = _parse_date(payload.get("end_date"), "end_date")
        validate_status_dates(status, start_date, end_date)

        return cls(
            full_name=_normalize_full_name(payload.get("full_name")),
            employee_ref=_normalize_employee_ref(payload.get("employee_ref")),
            status=status,
            start_date=start_date,
            end_date=end_date,
        )


@dataclass(frozen=True)
class EmployeeUpdateRequest:
    """Validated payload for employee updates."""

    full_name: str | None = None
    employee_ref: str | None = None
    status: str | None = None
    start_date: date | None = None
    end_date: date | None = None

    @classmethod
    def from_dict(cls, payload: dict) -> "EmployeeUpdateRequest":
        full_name_raw = payload.get("full_name")
        status_raw = payload.get("status")
        start_date_raw = payload.get("start_date")
        end_date_raw = payload.get("end_date")
        employee_ref_raw = payload.get("employee_ref")

        full_name = None
        if full_name_raw is not None:
            full_name = _normalize_full_name(full_name_raw)

        status = None
        if status_raw is not None:
            status = _normalize_status(status_raw)

        start_date = _parse_date(start_date_raw, "start_date")
        end_date = _parse_date(end_date_raw, "end_date")
        employee_ref = (
            _normalize_employee_ref(employee_ref_raw) if employee_ref_raw is not None else None
        )

        if (
            full_name is None
            and employee_ref is None
            and status is None
            and start_date is None
            and end_date is None
        ):
            raise BadRequest("no_fields_to_update")

        return cls(
            full_name=full_name,
            employee_ref=employee_ref,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )


@dataclass(frozen=True)
class EmployeeTerminateRequest:
    """Validated payload for employee termination."""

    end_date: date

    @classmethod
    def from_dict(cls, payload: dict) -> "EmployeeTerminateRequest":
        end_date = _parse_date(payload.get("end_date"), "end_date")
        if end_date is None:
            raise BadRequest("end_date_required")
        return cls(end_date=end_date)


class EmployeeResponseSchema:
    """Serializer for employee responses."""

    @staticmethod
    def dump(employee: Employee) -> dict:
        return {
            "id": employee.id,
            "client_id": employee.client_id,
            "company_id": employee.company_id,
            "full_name": employee.full_name,
            "employee_ref": employee.employee_ref,
            "status": employee.status,
            "start_date": _format_date(employee.start_date),
            "end_date": _format_date(employee.end_date),
            "created_at": _format_datetime(employee.created_at),
            "updated_at": _format_datetime(employee.updated_at),
        }
