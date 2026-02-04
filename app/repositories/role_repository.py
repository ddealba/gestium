"""Role repository."""

from __future__ import annotations

from app.extensions import db
from app.models.role import Role


class RoleRepository:
    """Data access layer for Role."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def get_by_id(self, role_id: str) -> Role | None:
        return self.session.query(Role).filter(Role.id == role_id).one_or_none()

    def get_by_name(self, name: str, scope: str, client_id: str | None) -> Role | None:
        return (
            self.session.query(Role)
            .filter(Role.name == name, Role.scope == scope, Role.client_id == client_id)
            .one_or_none()
        )

    def list_for_client(self, client_id: str) -> list[Role]:
        return (
            self.session.query(Role)
            .filter(Role.scope == "tenant", Role.client_id == client_id)
            .order_by(Role.name.asc())
            .all()
        )
