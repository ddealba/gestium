"""User service layer."""

from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash

from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    """Service layer for user operations."""

    def __init__(self, repository: UserRepository | None = None) -> None:
        self.repository = repository or UserRepository()

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    def create_invited_user(self, client_id: str, email: str) -> User:
        normalized_email = self.normalize_email(email)
        user = User(
            client_id=client_id,
            email=normalized_email,
            status="invited",
            password_hash=None,
        )
        return self.repository.create(user)

    def activate_user(self, user_id: str, client_id: str, password: str) -> User | None:
        user = self.repository.get_by_id(user_id, client_id)
        if not user:
            return None
        user.password_hash = generate_password_hash(password)
        user.status = "active"
        return self.repository.update(user)

    def disable_user(self, user_id: str, client_id: str) -> User | None:
        user = self.repository.get_by_id(user_id, client_id)
        if not user:
            return None
        user.status = "disabled"
        return self.repository.update(user)

    def verify_password(self, user: User, password: str) -> bool:
        if not user.password_hash:
            return False
        return check_password_hash(user.password_hash, password)
