"""Service layer for employee operations."""

from __future__ import annotations

from werkzeug.exceptions import NotFound

from app.models.employee import Employee
from app.modules.companies.repository import CompanyRepository
from app.modules.employees.repository import EmployeeRepository
from app.modules.employees.schemas import (
    EmployeeCreateRequest,
    EmployeeTerminateRequest,
    EmployeeUpdateRequest,
    validate_status_dates,
)


class EmployeeService:
    """Employee service for CRUD operations."""

    def __init__(
        self,
        repository: EmployeeRepository | None = None,
        company_repository: CompanyRepository | None = None,
    ) -> None:
        self.repository = repository or EmployeeRepository()
        self.company_repository = company_repository or CompanyRepository()

    def list_employees(self, client_id: str, company_id: str) -> list[Employee]:
        self._ensure_company(client_id, company_id)
        return self.repository.list_by_company(company_id, client_id)

    def create_employee(
        self,
        client_id: str,
        company_id: str,
        payload: EmployeeCreateRequest,
    ) -> Employee:
        self._ensure_company(client_id, company_id)
        employee = Employee(
            client_id=client_id,
            company_id=company_id,
            full_name=payload.full_name,
            employee_ref=payload.employee_ref,
            status=payload.status,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
        self.repository.create(employee)
        # TODO: AuditService.log_employee_created(employee)
        return employee

    def get_employee(self, client_id: str, company_id: str, employee_id: str) -> Employee:
        self._ensure_company(client_id, company_id)
        employee = self.repository.get_by_id(employee_id, client_id)
        if employee is None or employee.company_id != company_id:
            raise NotFound("Employee not found.")
        return employee

    def update_employee(
        self,
        client_id: str,
        company_id: str,
        employee_id: str,
        payload: EmployeeUpdateRequest,
    ) -> Employee:
        employee = self.get_employee(client_id, company_id, employee_id)
        if payload.full_name is not None:
            employee.full_name = payload.full_name
        if payload.employee_ref is not None:
            employee.employee_ref = payload.employee_ref
        if payload.status is not None:
            employee.status = payload.status
        if payload.start_date is not None:
            employee.start_date = payload.start_date
        if (
            payload.end_date is not None
            or payload.status is not None
            or payload.start_date is not None
        ):
            end_date = payload.end_date if payload.end_date is not None else employee.end_date
            if employee.status == "active" and payload.end_date is None:
                end_date = None
            validate_status_dates(employee.status, employee.start_date, end_date)
            if payload.end_date is not None or employee.status == "active":
                employee.end_date = end_date
        self.repository.update(employee)
        # TODO: AuditService.log_employee_updated(employee)
        return employee

    def terminate_employee(
        self,
        client_id: str,
        company_id: str,
        employee_id: str,
        payload: EmployeeTerminateRequest,
    ) -> Employee:
        employee = self.get_employee(client_id, company_id, employee_id)
        employee.status = "terminated"
        validate_status_dates(employee.status, employee.start_date, payload.end_date)
        employee.end_date = payload.end_date
        self.repository.update(employee)
        # TODO: AuditService.log_employee_terminated(employee)
        return employee

    def _ensure_company(self, client_id: str, company_id: str) -> None:
        company = self.company_repository.get_by_id(company_id, client_id)
        if company is None:
            raise NotFound("Company not found.")
