"""Repository for company data access."""

from __future__ import annotations

from werkzeug.exceptions import BadRequest
from sqlalchemy import false, or_

from app.extensions import db
from app.models.company import Company

VALID_SORT_FIELDS = {"name", "created_at", "status"}
VALID_ORDERS = {"asc", "desc"}


class CompanyRepository:
    """Data access layer for Company."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def create(self, company: Company) -> Company:
        self.session.add(company)
        self.session.flush()
        return company

    def update(self, company: Company) -> Company:
        self.session.add(company)
        self.session.flush()
        return company

    def get_by_id(self, company_id: str, client_id: str) -> Company | None:
        return (
            self.session.query(Company)
            .filter(Company.id == company_id, Company.client_id == client_id)
            .one_or_none()
        )

    def list(
        self,
        client_id: str,
        allowed_company_ids: set[str] | None = None,
        status: str | None = None,
        q: str | None = None,
    ) -> list[Company]:
        query = self.session.query(Company).filter(Company.client_id == client_id)

        if allowed_company_ids is not None:
            if not allowed_company_ids:
                return query.filter(false()).all()
            query = query.filter(Company.id.in_(allowed_company_ids))

        if status:
            query = query.filter(Company.status == status)

        if q:
            like_query = f"%{q}%"
            query = query.filter(
                or_(
                    Company.name.ilike(like_query),
                    Company.tax_id.ilike(like_query),
                )
            )

        return query.order_by(Company.name.asc()).all()

    def list_by_client(
        self,
        client_id: str,
        q: str | None = None,
        status: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
        limit: int = 20,
        offset: int = 0,
        allowed_company_ids: set[str] | None = None,
    ) -> tuple[list[Company], int]:
        query = self.session.query(Company).filter(Company.client_id == client_id)

        if allowed_company_ids is not None:
            if not allowed_company_ids:
                return [], 0
            query = query.filter(Company.id.in_(allowed_company_ids))

        if status:
            query = query.filter(Company.status == status)

        if q is not None:
            q_value = q.strip()
            if q_value:
                like_query = f"%{q_value}%"
                query = query.filter(or_(Company.name.ilike(like_query), Company.tax_id.ilike(like_query)))

        if sort not in VALID_SORT_FIELDS:
            raise BadRequest("invalid_sort")

        if order not in VALID_ORDERS:
            raise BadRequest("invalid_order")

        sort_column = getattr(Company, sort)
        direction = sort_column.asc() if order == "asc" else sort_column.desc()
        fallback_direction = Company.created_at.asc() if order == "asc" else Company.created_at.desc()

        total_count = query.count()
        items = (
            query.order_by(direction, fallback_direction)
            .limit(max(limit, 1))
            .offset(max(offset, 0))
            .all()
        )
        return items, total_count
