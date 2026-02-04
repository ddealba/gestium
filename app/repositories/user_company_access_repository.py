"""Repository for user-company access records."""

from __future__ import annotations

from app.extensions import db
from app.models.user_company_access import UserCompanyAccess


class UserCompanyAccessRepository:
    """Data access layer for UserCompanyAccess."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def get_user_access(
        self,
        user_id: str,
        company_id: str,
        client_id: str,
    ) -> UserCompanyAccess | None:
        return (
            self.session.query(UserCompanyAccess)
            .filter(
                UserCompanyAccess.user_id == user_id,
                UserCompanyAccess.company_id == company_id,
                UserCompanyAccess.client_id == client_id,
            )
            .one_or_none()
        )

    def list_company_ids_for_user(self, user_id: str, client_id: str) -> list[str]:
        rows = (
            self.session.query(UserCompanyAccess.company_id)
            .filter(
                UserCompanyAccess.user_id == user_id,
                UserCompanyAccess.client_id == client_id,
            )
            .all()
        )
        return [row[0] for row in rows]

    def upsert_access(
        self,
        user_id: str,
        company_id: str,
        client_id: str,
        access_level: str,
    ) -> UserCompanyAccess:
        access = self.get_user_access(user_id, company_id, client_id)
        if access is None:
            access = UserCompanyAccess(
                user_id=user_id,
                company_id=company_id,
                client_id=client_id,
                access_level=access_level,
            )
            self.session.add(access)
        else:
            access.access_level = access_level
            self.session.add(access)
        self.session.flush()
        return access

    def remove_access(self, user_id: str, company_id: str, client_id: str) -> bool:
        access = self.get_user_access(user_id, company_id, client_id)
        if access is None:
            return False
        self.session.delete(access)
        self.session.flush()
        return True
