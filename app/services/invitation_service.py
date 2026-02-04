"""Invitation service layer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from werkzeug.exceptions import BadRequest, Conflict
from werkzeug.security import generate_password_hash

from app.models.user import User
from app.models.user_invitation import UserInvitation
from app.repositories.user_invitation_repository import UserInvitationRepository
from app.repositories.user_repository import UserRepository


EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


@dataclass(frozen=True)
class InvitationResult:
    invitation: UserInvitation
    token: str


class InvitationService:
    """Service layer for invitation workflows."""

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        invitation_repository: UserInvitationRepository | None = None,
    ) -> None:
        self.user_repository = user_repository or UserRepository()
        self.invitation_repository = invitation_repository or UserInvitationRepository()

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def validate_email(email: str) -> None:
        import re

        if not re.match(EMAIL_PATTERN, email or ""):
            raise BadRequest("email_invalid")

    @staticmethod
    def validate_password(password: str) -> None:
        if not password or len(password) < 8:
            raise BadRequest("password_too_short")

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _current_time(reference: datetime | None = None) -> datetime:
        if reference is not None and reference.tzinfo is None:
            return datetime.now(timezone.utc).replace(tzinfo=None)
        return datetime.now(timezone.utc)

    def _ensure_user_invitable(self, user: User | None) -> User | None:
        if user is None:
            return None
        if user.status == "active":
            raise Conflict("user_active")
        if user.status == "disabled":
            raise Conflict("user_disabled")
        return user

    def create_invitation(self, client_id: str, email: str, ttl_hours: int = 48) -> InvitationResult:
        self.validate_email(email)
        normalized_email = self.normalize_email(email)
        existing_user = self.user_repository.get_by_email(normalized_email, client_id)
        existing_user = self._ensure_user_invitable(existing_user)

        if existing_user is None:
            existing_user = User(
                client_id=client_id,
                email=normalized_email,
                status="invited",
                password_hash=None,
            )
            self.user_repository.create(existing_user)

        token = self.generate_token()
        token_hash = self.hash_token(token)
        now = self._current_time()
        invitation = UserInvitation(
            client_id=client_id,
            email=normalized_email,
            token_hash=token_hash,
            expires_at=now + timedelta(hours=ttl_hours),
            used_at=None,
        )
        self.invitation_repository.create(invitation)
        return InvitationResult(invitation=invitation, token=token)

    def consume_invitation(self, client_id: str, token: str, password: str) -> User:
        if not token:
            raise BadRequest("token_required")
        self.validate_password(password)

        token_hash = self.hash_token(token)
        invitation = self.invitation_repository.get_by_token_hash(client_id, token_hash)
        if invitation is None:
            raise BadRequest("token_invalid")
        if invitation.used_at is not None:
            raise BadRequest("token_used")

        now = self._current_time(invitation.expires_at)
        if invitation.expires_at <= now:
            raise BadRequest("token_expired")

        user = self.user_repository.get_by_email(invitation.email, client_id)
        if user is None:
            raise BadRequest("invited_user_missing")
        if user.status == "disabled":
            raise Conflict("user_disabled")

        user.password_hash = generate_password_hash(password)
        user.status = "active"
        self.user_repository.update(user)

        invitation.used_at = self._current_time(invitation.expires_at)
        self.invitation_repository.update(invitation)
        return user
