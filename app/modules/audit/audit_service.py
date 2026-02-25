"""Audit logging service."""

from __future__ import annotations

from flask import current_app

from app.extensions import db
from app.modules.audit.models import AuditLog


class AuditService:
    """Write/read helpers for audit records."""

    def log_action(
        self,
        client_id: str,
        actor_user_id: str | None,
        action: str,
        entity_type: str,
        entity_id: str,
        metadata: dict | None = None,
    ) -> None:
        """Best-effort audit writer that never interrupts primary business flow."""
        try:
            record = AuditLog(
                client_id=client_id,
                actor_user_id=actor_user_id,
                action=(action or "").strip() or "unknown_action",
                entity_type=(entity_type or "").strip() or "unknown_entity",
                entity_id=(entity_id or "").strip() or "unknown_id",
                metadata_json=metadata or {},
            )
            db.session.add(record)
        except Exception:  # noqa: BLE001
            current_app.logger.exception("audit_log_write_failed")

    def list_actions(
        self,
        client_id: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        user_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditLog]:
        query = AuditLog.query.filter(AuditLog.client_id == client_id)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        if entity_id:
            query = query.filter(AuditLog.entity_id == entity_id)
        if user_id:
            query = query.filter(AuditLog.actor_user_id == user_id)

        return query.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
