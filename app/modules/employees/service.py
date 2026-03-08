"""Service layer for employee operations."""

from __future__ import annotations

from datetime import date

from werkzeug.exceptions import NotFound

from app.models.employee import Employee
from app.models.person_company_relation import PersonCompanyRelation
from app.modules.audit.audit_service import AuditService
from app.modules.companies.repository import CompanyRepository
from app.modules.employees.repository import EmployeeRepository
from app.modules.employees.schemas import (
    EmployeeCreateRequest,
    EmployeeTerminateRequest,
    EmployeeUpdateRequest,
    validate_status_dates,
)
from app.modules.person.person_repository import PersonRepository
from app.modules.person_company_relation.relation_repository import PersonCompanyRelationRepository


class EmployeeService:
    """Employee service for CRUD operations."""

    def __init__(
        self,
        repository: EmployeeRepository | None = None,
        company_repository: CompanyRepository | None = None,
        person_repository: PersonRepository | None = None,
        relation_repository: PersonCompanyRelationRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.repository = repository or EmployeeRepository()
        self.company_repository = company_repository or CompanyRepository()
        self.person_repository = person_repository or PersonRepository()
        self.relation_repository = relation_repository or PersonCompanyRelationRepository()
        self.audit_service = audit_service or AuditService()

    def list_employees(
        self,
        client_id: str,
        company_id: str,
        q: str | None = None,
        status: str | None = None,
        sort: str = "name",
        order: str = "asc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Employee], int]:
        self._ensure_company(client_id, company_id)
        return self.repository.list_by_company(
            company_id=company_id,
            client_id=client_id,
            q=q,
            status=status,
            sort=sort,
            order=order,
            limit=limit,
            offset=offset,
        )

    def create_employee(
        self,
        client_id: str,
        company_id: str,
        payload: EmployeeCreateRequest,
        actor_user_id: str | None = None,
    ) -> Employee:
        self._ensure_company(client_id, company_id)

        person = None
        if payload.person_id is not None:
            person = self._ensure_person(client_id, payload.person_id)
            self._ensure_employee_relation(
                client_id=client_id,
                user_id=actor_user_id,
                person_id=person.id,
                company_id=company_id,
                start_date=payload.start_date,
            )

        full_name = payload.full_name or (f"{person.first_name} {person.last_name}".strip() if person else None)

        employee = Employee(
            client_id=client_id,
            company_id=company_id,
            person_id=person.id if person is not None else None,
            full_name=full_name,
            employee_ref=payload.employee_ref,
            status=payload.status,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
        self.repository.create(employee)
        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=actor_user_id,
            action="employee_created",
            entity_type="employee",
            entity_id=employee.id,
            metadata={
                "company_id": company_id,
                "person_id": employee.person_id,
                "status": employee.status,
                "legacy_employee": employee.person_id is None,
            },
        )
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
        actor_user_id: str | None = None,
    ) -> Employee:
        employee = self.get_employee(client_id, company_id, employee_id)
        person_link_changed = False

        if payload.update_person_id:
            employee.person_id = None
            if payload.person_id is not None:
                person = self._ensure_person(client_id, payload.person_id)
                self._ensure_employee_relation(
                    client_id=client_id,
                    user_id=actor_user_id,
                    person_id=person.id,
                    company_id=company_id,
                    start_date=employee.start_date,
                )
                employee.person_id = person.id
                if payload.full_name is None:
                    employee.full_name = f"{person.first_name} {person.last_name}".strip()
            person_link_changed = True

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

        if person_link_changed:
            self.audit_service.log_action(
                client_id=client_id,
                actor_user_id=actor_user_id,
                action="employee_person_linked",
                entity_type="employee",
                entity_id=employee.id,
                metadata={"person_id": employee.person_id, "company_id": employee.company_id},
            )

        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=actor_user_id,
            action="employee_updated",
            entity_type="employee",
            entity_id=employee.id,
            metadata={"status": employee.status, "person_id": employee.person_id},
        )
        return employee

    def terminate_employee(
        self,
        client_id: str,
        company_id: str,
        employee_id: str,
        payload: EmployeeTerminateRequest,
        actor_user_id: str | None = None,
    ) -> Employee:
        employee = self.get_employee(client_id, company_id, employee_id)
        employee.status = "terminated"
        validate_status_dates(employee.status, employee.start_date, payload.end_date)
        employee.end_date = payload.end_date
        self.repository.update(employee)
        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=actor_user_id,
            action="employee_terminated",
            entity_type="employee",
            entity_id=employee.id,
            metadata={"end_date": employee.end_date.isoformat()},
        )
        return employee

    def _ensure_company(self, client_id: str, company_id: str) -> None:
        company = self.company_repository.get_by_id(company_id, client_id)
        if company is None:
            raise NotFound("Company not found.")

    def _ensure_person(self, client_id: str, person_id: str):
        person = self.person_repository.get_person_by_id(person_id, client_id)
        if person is None:
            raise NotFound("Person not found.")
        return person

    def _ensure_employee_relation(
        self,
        client_id: str,
        user_id: str | None,
        person_id: str,
        company_id: str,
        start_date: date,
    ) -> PersonCompanyRelation:
        relation = self.relation_repository.find_active_relation(
            client_id=client_id,
            person_id=person_id,
            company_id=company_id,
            relation_type="employee",
        )
        if relation is not None:
            return relation

        relation = PersonCompanyRelation(
            client_id=client_id,
            person_id=person_id,
            company_id=company_id,
            relation_type="employee",
            status="active",
            start_date=start_date,
            created_by=user_id,
        )
        self.relation_repository.create_relation(relation)
        return relation
