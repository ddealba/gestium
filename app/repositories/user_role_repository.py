"""User role repository."""

from __future__ import annotations

from app.extensions import db
from app.models.role import Role
from app.models.user import User


class UserRoleRepository:
    """Data access layer for user-role assignments."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def assign_role(self, user_id: str, role_id: str) -> None:
        user = self.session.get(User, user_id)
        role = self.session.get(Role, role_id)
        if user is None or role is None:
            return
        if role not in user.roles:
            user.roles.append(role)
            self.session.flush()

    def remove_role(self, user_id: str, role_id: str) -> None:
        user = self.session.get(User, user_id)
        role = self.session.get(Role, role_id)
        if user is None or role is None:
            return
        if role in user.roles:
            user.roles.remove(role)
            self.session.flush()

    def list_user_roles(self, user_id: str) -> list[Role]:
        user = self.session.get(User, user_id)
        if user is None:
            return []
        return list(user.roles)
