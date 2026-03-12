"""Legacy compatibility wrapper around consolidated portal services."""

from __future__ import annotations

from app.modules.portal.context import PortalContext
from app.modules.portal.portal_service import PortalService


class FrontofficeService:
    """Deprecated alias for ``PortalService``."""

    def __init__(self) -> None:
        self._service = PortalService()

    @staticmethod
    def _context(user, client_id: str) -> PortalContext:
        return PortalContext.from_user(user, client_id)

    def get_portal_profile(self, user, client_id: str) -> dict:
        return self._service.get_portal_profile(self._context(user, client_id))

    def get_portal_documents(self, user, client_id: str, section: str | None = None) -> list[dict]:
        return self._service.get_portal_documents(self._context(user, client_id), scope=section)

    def get_portal_cases(self, user, client_id: str, section: str | None = None) -> list[dict]:
        return self._service.get_portal_cases(self._context(user, client_id), scope=section)

    def get_portal_companies(self, user, client_id: str) -> list[dict]:
        return self._service.get_portal_companies(self._context(user, client_id))

    def get_portal_company_detail(self, user, client_id: str, company_id: str) -> dict:
        return self._service.get_portal_company_detail(self._context(user, client_id), company_id)

    def get_portal_summary(self, user, client_id: str) -> dict:
        return self._service.get_portal_summary(self._context(user, client_id))

    def get_portal_home(self, user, client_id: str) -> dict:
        return self._service.get_portal_home(self._context(user, client_id))
