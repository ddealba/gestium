"""Health routes."""

from flask import Blueprint, g

from app.common.responses import ok
from app.common.tenant import tenant_required
from app.modules.health.service import get_health_status

bp = Blueprint("health", __name__)


@bp.get("/health")
def health_check():
    return ok(get_health_status())


@bp.get("/health/tenant")
@tenant_required
def tenant_health_check():
    return ok({"client_id": str(g.client_id)})
