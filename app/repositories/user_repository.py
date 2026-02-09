"""User repository."""

from __future__ import annotations

from app.extensions import db
from app.models.user import User


class UserRepository:
    """Data access layer for User."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def get_by_id(self, user_id: str, client_id: str) -> User | None:
        return (
            self.session.query(User)
            .filter(User.id == user_id, User.client_id == client_id)
            .one_or_none()
        )

    def get_by_email(self, email: str, client_id: str) -> User | None:
        return (
            self.session.query(User)
            .filter(User.email == email, User.client_id == client_id)
            .one_or_none()
        )

    def list_active_by_email(self, email: str) -> list[User]:
        return (
            self.session.query(User)
            .filter(User.email == email, User.status == "active")
            .all()
        )

    def create(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user

    def update(self, user: User) -> User:
        self.session.add(user)
        self.session.flush()
        return user
