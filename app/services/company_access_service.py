"""Service layer for company access checks."""

from __future__ import annotations

from werkzeug.exceptions import Forbidden, NotFound

from app.common.access_levels import access_level_ge
from app.repositories.user_company_access_repository import UserCompanyAccessRepository


class CompanyAccessService:
    """Service for evaluating company access levels."""

    def __init__(self, repository: UserCompanyAccessRepository | None = None) -> None:
        self.repository = repository or UserCompanyAccessRepository()

    def require_access(
        self,
        user_id: str,
        company_id: str,
        client_id: str,
        required_level: str,
    ):
        access = self.repository.get_user_access(user_id, company_id, client_id)
        if access is None:
            raise NotFound("Company access not found.")
        if not access_level_ge(access.access_level, required_level):
            raise Forbidden("Insufficient access level.")
        return access

    def get_allowed_company_ids(self, user_id: str, client_id: str) -> set[str]:
        return set(self.repository.list_company_ids_for_user(user_id, client_id))
