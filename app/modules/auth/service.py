"""Authentication service."""

from __future__ import annotations

from werkzeug.exceptions import BadRequest, Forbidden, Unauthorized

from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


class AuthService:
    """Service layer for authentication workflows."""

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        user_service: UserService | None = None,
    ) -> None:
        self.user_repository = user_repository or UserRepository()
        self.user_service = user_service or UserService(self.user_repository)

    def authenticate(self, email: str, password: str, client_id: str | None) -> tuple[str, str]:
        if not email:
            raise BadRequest("email_required")
        if not password:
            raise BadRequest("password_required")
        normalized_email = self.user_service.normalize_email(email)

        resolved_client_id = client_id
        if resolved_client_id:
            user = self.user_repository.get_by_email(normalized_email, resolved_client_id)
        else:
            users = self.user_repository.list_active_by_email(normalized_email)
            if len(users) > 1:
                raise BadRequest("client_id_required")
            user = users[0] if users else None
            resolved_client_id = user.client_id if user is not None else None
        if user is None or not self.user_service.verify_password(user, password):
            raise Unauthorized("invalid_credentials")
        if user.status != "active":
            raise Forbidden("user_inactive")

        return user.id, resolved_client_id
