"""Dashboard API routes."""

from __future__ import annotations

from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest

from app.common.decorators import auth_required, require_permission
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.modules.dashboard.service import DashboardService

bp = Blueprint("dashboard", __name__)


def _parse_int_arg(name: str, default: int) -> int:
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise BadRequest(f"invalid_{name}") from exc
    if value <= 0:
        raise BadRequest(f"invalid_{name}")
    return value


@bp.get("/dashboard/summary")
@auth_required
@tenant_required
@require_permission("dashboard.read")
def get_dashboard_summary():
    service = DashboardService()
    payload = service.get_summary(
        client_id=str(g.client_id),
        user_id=str(g.user.id),
        days=_parse_int_arg("days", 14),
        overdue_limit=_parse_int_arg("overdue_limit", 8),
        activity_limit=_parse_int_arg("activity_limit", 12),
        my_cases_limit=_parse_int_arg("my_cases_limit", 5),
    )
    return ok(payload)
