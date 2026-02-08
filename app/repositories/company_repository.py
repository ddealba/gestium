"""Repository for company data access."""

from __future__ import annotations

from sqlalchemy import false

from app.models.company import Company
from app.modules.companies.repository import CompanyRepository as ModuleCompanyRepository


class CompanyRepository(ModuleCompanyRepository):
    """# DEPRECATED: use app.modules.companies.repository.CompanyRepository."""

    def list_query(self, client_id: str):
        return self.session.query(Company).filter(Company.client_id == client_id)

    def add(self, company: Company) -> Company:
        return self.update(company)

    @staticmethod
    def filter_by_allowed_companies(query, allowed_company_ids: set[str]):
        if not allowed_company_ids:
            return query.filter(false())
        return query.filter(Company.id.in_(allowed_company_ids))
