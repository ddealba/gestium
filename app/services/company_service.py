"""Service layer for company operations."""

from __future__ import annotations

from app.models.company import Company
from app.modules.companies.service import CompanyService as ModuleCompanyService


class CompanyService(ModuleCompanyService):
    """# DEPRECATED: use app.modules.companies.service.CompanyService."""

    def list_companies(self, user_id: str, client_id: str) -> list[Company]:
        return super().list_companies(client_id=client_id, user_id=user_id)

    def get_company(self, company_id: str, client_id: str) -> Company:
        return super().get_company(client_id=client_id, company_id=company_id)

    def update_company_name(self, company: Company, name: str) -> Company:
        company.name = name
        self.repository.update(company)
        return company
