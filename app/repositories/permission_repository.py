"""Permission repository."""

from __future__ import annotations

from app.extensions import db
from app.models.permission import Permission


class PermissionRepository:
    """Data access layer for Permission."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def get_by_code(self, code: str) -> Permission | None:
        return self.session.query(Permission).filter(Permission.code == code).one_or_none()

    def list_all(self) -> list[Permission]:
        return self.session.query(Permission).order_by(Permission.code.asc()).all()
