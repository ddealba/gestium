"""Portal audit helper service."""

from __future__ import annotations

from app.modules.audit.audit_service import AuditService
from app.modules.portal.context import PortalContext


class PortalAuditService:
    """Centralize audit events emitted by portal interactions."""

    def __init__(self, audit_service: AuditService | None = None) -> None:
        self.audit_service = audit_service or AuditService()

    def log(self, action: str, context: PortalContext, entity_type: str, entity_id: str, metadata: dict | None = None) -> None:
        self.audit_service.log_action(
            client_id=context.client_id,
            actor_user_id=context.user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
        )
