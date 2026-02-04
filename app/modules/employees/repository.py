"""Repository for employee data access."""

from __future__ import annotations

from app.extensions import db
from app.models.employee import Employee


class EmployeeRepository:
    """Data access layer for Employee."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def create(self, employee: Employee) -> Employee:
        self.session.add(employee)
        self.session.flush()
        return employee

    def update(self, employee: Employee) -> Employee:
        self.session.add(employee)
        self.session.flush()
        return employee

    def get_by_id(self, employee_id: str, client_id: str) -> Employee | None:
        return (
            self.session.query(Employee)
            .filter(Employee.id == employee_id, Employee.client_id == client_id)
            .one_or_none()
        )

    def list_by_company(self, company_id: str, client_id: str) -> list[Employee]:
        return (
            self.session.query(Employee)
            .filter(Employee.company_id == company_id, Employee.client_id == client_id)
            .order_by(Employee.full_name.asc())
            .all()
        )
