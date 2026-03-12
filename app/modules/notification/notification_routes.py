"""Notification endpoints."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request
from werkzeug.exceptions import BadRequest

from app.common.decorators import auth_required, require_user_type
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.extensions import db
from app.modules.notification.notification_service import ALLOWED_PRIORITY, ALLOWED_STATUS, NotificationService, serialize_notification

bp = Blueprint("notification", __name__)


def _validate_filters() -> tuple[str | None, str | None]:
    status = request.args.get("status")
    priority = request.args.get("priority")
    if status and status not in ALLOWED_STATUS:
        raise BadRequest("invalid_status")
    if priority and priority not in ALLOWED_PRIORITY:
        raise BadRequest("invalid_priority")
    return status, priority


@bp.get("/portal/api/notifications")
@auth_required
@tenant_required
@require_user_type("portal")
def list_portal_notifications():
    status, priority = _validate_filters()
    items = NotificationService().list_notifications_for_portal(
        client_id=str(g.client_id),
        person_id=str(g.user.person_id),
        status=status,
        priority=priority,
    )
    return jsonify([serialize_notification(item) for item in items])


@bp.post("/portal/api/notifications/<notification_id>/read")
@auth_required
@tenant_required
@require_user_type("portal")
def read_portal_notification(notification_id: str):
    item = NotificationService().mark_as_read(
        client_id=str(g.client_id),
        notification_id=notification_id,
        person_id=str(g.user.person_id),
    )
    db.session.commit()
    return ok(serialize_notification(item))


@bp.post("/portal/api/notifications/<notification_id>/dismiss")
@auth_required
@tenant_required
@require_user_type("portal")
def dismiss_portal_notification(notification_id: str):
    item = NotificationService().dismiss_notification(
        client_id=str(g.client_id),
        notification_id=notification_id,
        person_id=str(g.user.person_id),
    )
    db.session.commit()
    return ok(serialize_notification(item))


@bp.get("/api/notifications")
@auth_required
@tenant_required
def list_backoffice_notifications():
    status, priority = _validate_filters()
    items = NotificationService().list_notifications_for_user(
        client_id=str(g.client_id),
        user_id=str(g.user.id),
        status=status,
        priority=priority,
    )
    return jsonify([serialize_notification(item) for item in items])


@bp.post("/api/notifications/<notification_id>/read")
@auth_required
@tenant_required
def read_backoffice_notification(notification_id: str):
    item = NotificationService().mark_as_read(
        client_id=str(g.client_id),
        notification_id=notification_id,
        user_id=str(g.user.id),
    )
    db.session.commit()
    return ok(serialize_notification(item))


@bp.post("/api/notifications/<notification_id>/dismiss")
@auth_required
@tenant_required
def dismiss_backoffice_notification(notification_id: str):
    item = NotificationService().dismiss_notification(
        client_id=str(g.client_id),
        notification_id=notification_id,
        user_id=str(g.user.id),
    )
    db.session.commit()
    return ok(serialize_notification(item))
