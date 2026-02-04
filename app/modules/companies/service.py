"""Service layer for company operations."""

from __future__ import annotations

from werkzeug.exceptions import NotFound

from app.models.company import Company
from app.modules.companies.repository import CompanyRepository
from app.modules.companies.schemas import CompanyCreatePayload, CompanyUpdatePayload
from app.repositories.user_company_access_repository import UserCompanyAccessRepository
from app.services.company_access_service import CompanyAccessService


class CompanyService:
    """Company service for CRUD operations."""

    def __init__(
        self,
        repository: CompanyRepository | None = None,
        access_repository: UserCompanyAccessRepository | None = None,
        access_service: CompanyAccessService | None = None,
    ) -> None:
        self.repository = repository or CompanyRepository()
        self.access_repository = access_repository or UserCompanyAccessRepository()
        self.access_service = access_service or CompanyAccessService()

    def list_companies(
        self,
        client_id: str,
        user_id: str,
        status: str | None = None,
        q: str | None = None,
    ) -> list[Company]:
        allowed_company_ids = self.access_service.get_allowed_company_ids(user_id, client_id)
        return self.repository.list(
            client_id=client_id,
            allowed_company_ids=allowed_company_ids,
            status=status,
            q=q,
        )

    def get_company(self, client_id: str, company_id: str) -> Company:
        company = self.repository.get_by_id(company_id, client_id)
        if company is None:
            raise NotFound("Company not found.")
        return company

    def create_company(
        self,
        client_id: str,
        user_id: str,
        payload: CompanyCreatePayload,
    ) -> Company:
        company = Company(
            client_id=client_id,
            name=payload.name,
            tax_id=payload.tax_id,
            status="active",
        )
        self.repository.create(company)
        self.access_repository.upsert_access(
            user_id=user_id,
            company_id=company.id,
            client_id=client_id,
            access_level="admin",
        )
        # TODO: AuditService.log_company_created(company, user_id)
        return company

    def update_company(
        self,
        client_id: str,
        company_id: str,
        payload: CompanyUpdatePayload,
    ) -> Company:
        company = self.get_company(client_id, company_id)
        if payload.name is not None:
            company.name = payload.name
        if payload.tax_id is not None:
            company.tax_id = payload.tax_id
        self.repository.update(company)
        # TODO: AuditService.log_company_updated(company)
        return company

    def deactivate_company(self, client_id: str, company_id: str) -> Company:
        company = self.get_company(client_id, company_id)
        company.status = "inactive"
        self.repository.update(company)
        # TODO: AuditService.log_company_deactivated(company)
        return company

    def activate_company(self, client_id: str, company_id: str) -> Company:
        company = self.get_company(client_id, company_id)
        company.status = "active"
        self.repository.update(company)
        # TODO: AuditService.log_company_activated(company)
        return company
