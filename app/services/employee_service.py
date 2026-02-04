"""Service layer for employee operations."""

from __future__ import annotations

from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeRepository


class EmployeeService:
    """Employee service for CRUD operations."""

    def __init__(self, repository: EmployeeRepository | None = None) -> None:
        self.repository = repository or EmployeeRepository()

    def create_employee(self, client_id: str, company_id: str, name: str) -> Employee:
        employee = Employee(client_id=client_id, company_id=company_id, name=name)
        return self.repository.add(employee)
