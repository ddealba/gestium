"""Service layer for company operations."""

from __future__ import annotations

from werkzeug.exceptions import NotFound

from app.common.acl import get_allowed_company_ids
from app.models.company import Company
from app.repositories.company_repository import CompanyRepository


class CompanyService:
    """Company service for CRUD operations."""

    def __init__(self, repository: CompanyRepository | None = None) -> None:
        self.repository = repository or CompanyRepository()

    def list_companies(self, user_id: str, client_id: str) -> list[Company]:
        allowed_company_ids = get_allowed_company_ids(user_id, client_id)
        query = self.repository.list_query(client_id)
        query = self.repository.filter_by_allowed_companies(query, allowed_company_ids)
        return query.all()

    def get_company(self, company_id: str, client_id: str) -> Company:
        company = self.repository.get_by_id(company_id, client_id)
        if company is None:
            raise NotFound("Company not found.")
        return company

    def update_company_name(self, company: Company, name: str) -> Company:
        company.name = name
        self.repository.add(company)
        return company
