"""Repository for employee data access."""

from __future__ import annotations

from sqlalchemy import false

from app.extensions import db
from app.models.employee import Employee


class EmployeeRepository:
    """Data access layer for Employee."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def add(self, employee: Employee) -> Employee:
        self.session.add(employee)
        self.session.flush()
        return employee

    @staticmethod
    def filter_by_allowed_companies(query, allowed_company_ids: set[str]):
        if not allowed_company_ids:
            return query.filter(false())
        return query.filter(Employee.company_id.in_(allowed_company_ids))
