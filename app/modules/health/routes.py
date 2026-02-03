"""Health routes."""

from flask import Blueprint

from app.common.responses import ok
from app.modules.health.service import get_health_status

bp = Blueprint("health", __name__)


@bp.get("/health")
def health_check():
    return ok(get_health_status())
