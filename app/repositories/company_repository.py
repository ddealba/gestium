"""Repository for company data access."""

from __future__ import annotations

from sqlalchemy import false

from app.extensions import db
from app.models.company import Company


class CompanyRepository:
    """Data access layer for Company."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def list_query(self, client_id: str):
        return self.session.query(Company).filter(Company.client_id == client_id)

    def get_by_id(self, company_id: str, client_id: str) -> Company | None:
        return (
            self.session.query(Company)
            .filter(Company.id == company_id, Company.client_id == client_id)
            .one_or_none()
        )

    def add(self, company: Company) -> Company:
        self.session.add(company)
        self.session.flush()
        return company

    @staticmethod
    def filter_by_allowed_companies(query, allowed_company_ids: set[str]):
        if not allowed_company_ids:
            return query.filter(false())
        return query.filter(Company.id.in_(allowed_company_ids))
