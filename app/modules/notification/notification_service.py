"""Notification service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from werkzeug.exceptions import NotFound

from app.extensions import db
from app.models.person_request import PersonRequest
from app.models.role import Role
from app.models.user import User
from app.modules.audit.audit_service import AuditService
from app.modules.notification.notification_model import Notification
from app.modules.notification.notification_repository import NotificationRepository

ALLOWED_STATUS = {"unread", "read", "dismissed"}
ALLOWED_PRIORITY = {"low", "medium", "high"}
DUE_SOON_DAYS = 3


class NotificationService:
    def __init__(self, repository: NotificationRepository | None = None, audit_service: AuditService | None = None) -> None:
        self.repository = repository or NotificationRepository()
        self.audit_service = audit_service or AuditService()

    def create_notification(self, **kwargs) -> Notification:
        item = Notification(**kwargs)
        self.repository.add(item)
        self.audit_service.log_action(
            client_id=kwargs["client_id"],
            actor_user_id=kwargs.get("user_id"),
            action="notification_created",
            entity_type="notification",
            entity_id=item.id,
            metadata={"notification_type": item.notification_type, "channel": item.channel},
        )
        return item

    def create_portal_notification(self, *, client_id: str, person_id: str, user_id: str | None = None, notification_type: str, title: str, message: str, entity_type: str | None = None, entity_id: str | None = None, priority: str = "medium", deduplicate: bool = False) -> Notification | None:
        if deduplicate and self.repository.find_existing(client_id, "internal_portal", notification_type, entity_type, entity_id, user_id, person_id):
            return None
        return self.create_notification(
            client_id=client_id,
            user_id=user_id,
            person_id=person_id,
            channel="internal_portal",
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            status="unread",
            priority=priority,
        )

    def create_backoffice_notification(self, *, client_id: str, user_id: str, notification_type: str, title: str, message: str, entity_type: str | None = None, entity_id: str | None = None, priority: str = "medium", deduplicate: bool = False) -> Notification | None:
        if deduplicate and self.repository.find_existing(client_id, "internal_backoffice", notification_type, entity_type, entity_id, user_id, None):
            return None
        return self.create_notification(
            client_id=client_id,
            user_id=user_id,
            person_id=None,
            channel="internal_backoffice",
            notification_type=notification_type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            status="unread",
            priority=priority,
        )

    def list_notifications_for_portal(self, *, client_id: str, person_id: str, status: str | None = None, priority: str | None = None) -> list[Notification]:
        self.generate_due_soon_notifications(client_id=client_id, person_id=person_id)
        self.generate_overdue_notifications(client_id=client_id, person_id=person_id)
        return self.repository.list_for_portal(client_id, person_id, status, priority)

    def list_notifications_for_user(self, *, client_id: str, user_id: str, status: str | None = None, priority: str | None = None) -> list[Notification]:
        return self.repository.list_for_user(client_id, user_id, status, priority)

    def mark_as_read(self, *, client_id: str, notification_id: str, user_id: str | None = None, person_id: str | None = None) -> Notification:
        item = self.repository.get_for_actor(client_id, notification_id, user_id=user_id, person_id=person_id)
        if item is None:
            raise NotFound("notification_not_found")
        item.status = "read"
        item.read_at = datetime.now(timezone.utc)
        self.audit_service.log_action(client_id=client_id, actor_user_id=user_id, action="notification_read", entity_type="notification", entity_id=item.id)
        return item

    def dismiss_notification(self, *, client_id: str, notification_id: str, user_id: str | None = None, person_id: str | None = None) -> Notification:
        item = self.repository.get_for_actor(client_id, notification_id, user_id=user_id, person_id=person_id)
        if item is None:
            raise NotFound("notification_not_found")
        item.status = "dismissed"
        self.audit_service.log_action(client_id=client_id, actor_user_id=user_id, action="notification_dismissed", entity_type="notification", entity_id=item.id)
        return item

    def generate_due_soon_notifications(self, *, client_id: str, person_id: str | None = None) -> int:
        today = datetime.now(timezone.utc).date()
        due_date_limit = today + timedelta(days=DUE_SOON_DAYS)
        query = db.session.query(PersonRequest).filter(
            PersonRequest.client_id == client_id,
            PersonRequest.status.in_(("pending", "rejected")),
            PersonRequest.due_date.isnot(None),
            PersonRequest.due_date >= today,
            PersonRequest.due_date <= due_date_limit,
        )
        if person_id:
            query = query.filter(PersonRequest.person_id == person_id)
        created = 0
        for item in query.all():
            created_item = self.create_portal_notification(
                client_id=client_id,
                person_id=item.person_id,
                notification_type="request_due_soon",
                title="Solicitud próxima a vencer",
                message=f"La solicitud '{item.title}' vence pronto.",
                entity_type="person_request",
                entity_id=item.id,
                priority="medium",
                deduplicate=True,
            )
            if created_item is not None:
                created += 1
        return created

    def generate_overdue_notifications(self, *, client_id: str, person_id: str | None = None) -> int:
        today = datetime.now(timezone.utc).date()
        query = db.session.query(PersonRequest).filter(
            PersonRequest.client_id == client_id,
            PersonRequest.status.in_(("pending", "rejected")),
            PersonRequest.due_date.isnot(None),
            PersonRequest.due_date < today,
        )
        if person_id:
            query = query.filter(PersonRequest.person_id == person_id)
        created = 0
        for item in query.all():
            portal_n = self.create_portal_notification(
                client_id=client_id,
                person_id=item.person_id,
                notification_type="request_overdue",
                title="Solicitud vencida",
                message=f"La solicitud '{item.title}' está vencida.",
                entity_type="person_request",
                entity_id=item.id,
                priority="high",
                deduplicate=True,
            )
            if portal_n is not None:
                created += 1
            if item.created_by:
                self.create_backoffice_notification(
                    client_id=client_id,
                    user_id=item.created_by,
                    notification_type="request_overdue",
                    title="Solicitud vencida sin resolver",
                    message=f"La solicitud '{item.title}' está vencida y pendiente.",
                    entity_type="person_request",
                    entity_id=item.id,
                    priority="high",
                    deduplicate=True,
                )
        return created

    def notify_profile_incomplete(self, *, client_id: str, person_id: str, completion_pct: int) -> None:
        self.create_portal_notification(
            client_id=client_id,
            person_id=person_id,
            notification_type="profile_incomplete",
            title="Tu perfil está incompleto",
            message="Completa tus datos para continuar con el onboarding.",
            entity_type="person",
            entity_id=person_id,
            priority="high" if completion_pct < 50 else "medium",
            deduplicate=True,
        )

        admin = (
            db.session.query(User)
            .join(User.roles)
            .filter(
                User.client_id == client_id,
                User.user_type == "internal",
                Role.name == "Admin Cliente",
            )
            .order_by(User.created_at.asc())
            .first()
        )
        if admin:
            self.create_backoffice_notification(
                client_id=client_id,
                user_id=admin.id,
                notification_type="profile_incomplete",
                title="Onboarding crítico incompleto",
                message="Una persona tiene onboarding incompleto crítico.",
                entity_type="person",
                entity_id=person_id,
                priority="high",
                deduplicate=True,
            )


def serialize_notification(item: Notification) -> dict:
    return {
        "id": item.id,
        "type": item.notification_type,
        "title": item.title,
        "message": item.message,
        "priority": item.priority,
        "status": item.status,
        "entity_type": item.entity_type,
        "entity_id": item.entity_id,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }
