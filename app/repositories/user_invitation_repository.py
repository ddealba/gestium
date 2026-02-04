"""User invitation repository."""

from __future__ import annotations

from datetime import datetime

from app.extensions import db
from app.models.user_invitation import UserInvitation


class UserInvitationRepository:
    """Data access layer for UserInvitation."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def create(self, invitation: UserInvitation) -> UserInvitation:
        self.session.add(invitation)
        self.session.flush()
        return invitation

    def update(self, invitation: UserInvitation) -> UserInvitation:
        self.session.add(invitation)
        self.session.flush()
        return invitation

    def get_active_by_email(self, client_id: str, email: str, now: datetime) -> UserInvitation | None:
        return (
            self.session.query(UserInvitation)
            .filter(
                UserInvitation.client_id == client_id,
                UserInvitation.email == email,
                UserInvitation.used_at.is_(None),
                UserInvitation.expires_at > now,
            )
            .order_by(UserInvitation.expires_at.desc())
            .first()
        )

    def get_by_token_hash(self, client_id: str, token_hash: str) -> UserInvitation | None:
        return (
            self.session.query(UserInvitation)
            .filter(
                UserInvitation.client_id == client_id,
                UserInvitation.token_hash == token_hash,
            )
            .one_or_none()
        )
