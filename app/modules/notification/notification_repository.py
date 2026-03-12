"""Notification repository."""

from __future__ import annotations

from app.extensions import db
from app.modules.notification.notification_model import Notification


class NotificationRepository:
    def add(self, item: Notification) -> Notification:
        db.session.add(item)
        return item

    def find_existing(
        self,
        client_id: str,
        channel: str,
        notification_type: str,
        entity_type: str | None,
        entity_id: str | None,
        user_id: str | None,
        person_id: str | None,
    ) -> Notification | None:
        query = db.session.query(Notification).filter(
            Notification.client_id == client_id,
            Notification.channel == channel,
            Notification.notification_type == notification_type,
            Notification.user_id == user_id,
            Notification.person_id == person_id,
            Notification.entity_type == entity_type,
            Notification.entity_id == entity_id,
        )
        return query.order_by(Notification.created_at.desc()).first()

    def get_for_actor(
        self,
        client_id: str,
        notification_id: str,
        user_id: str | None,
        person_id: str | None,
    ) -> Notification | None:
        query = db.session.query(Notification).filter(
            Notification.client_id == client_id,
            Notification.id == notification_id,
        )
        if user_id is not None:
            query = query.filter(Notification.user_id == user_id)
        if person_id is not None:
            query = query.filter(Notification.person_id == person_id)
        return query.one_or_none()

    def list_for_portal(self, client_id: str, person_id: str, status: str | None, priority: str | None) -> list[Notification]:
        query = db.session.query(Notification).filter(
            Notification.client_id == client_id,
            Notification.channel == "internal_portal",
            Notification.person_id == person_id,
        )
        if status:
            query = query.filter(Notification.status == status)
        if priority:
            query = query.filter(Notification.priority == priority)
        return query.order_by(Notification.created_at.desc()).all()

    def list_for_user(self, client_id: str, user_id: str, status: str | None, priority: str | None) -> list[Notification]:
        query = db.session.query(Notification).filter(
            Notification.client_id == client_id,
            Notification.channel == "internal_backoffice",
            Notification.user_id == user_id,
        )
        if status:
            query = query.filter(Notification.status == status)
        if priority:
            query = query.filter(Notification.priority == priority)
        return query.order_by(Notification.created_at.desc()).all()
