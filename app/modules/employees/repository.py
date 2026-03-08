"""Repository for employee data access."""

from __future__ import annotations

from sqlalchemy import and_, or_
from werkzeug.exceptions import BadRequest

from app.extensions import db
from app.models.employee import Employee
from app.models.person import Person
from app.models.person_company_relation import PersonCompanyRelation

VALID_SORT_FIELDS = {"name", "hire_date", "termination_date"}
VALID_ORDERS = {"asc", "desc"}
SORT_FIELD_MAP = {
    "name": Employee.full_name,
    "hire_date": Employee.start_date,
    "termination_date": Employee.end_date,
}


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
        row = (
            self._base_enriched_query(client_id)
            .filter(Employee.id == employee_id, Employee.client_id == client_id)
            .one_or_none()
        )
        return self._hydrate_row(row)

    def list_by_company(
        self,
        company_id: str,
        client_id: str,
        q: str | None = None,
        status: str | None = None,
        sort: str = "name",
        order: str = "asc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Employee], int]:
        query = self._base_enriched_query(client_id).filter(
            Employee.company_id == company_id,
            Employee.client_id == client_id,
        )

        if status:
            query = query.filter(Employee.status == status)

        if q is not None:
            q_value = q.strip()
            if q_value:
                like_query = f"%{q_value}%"
                query = query.filter(
                    or_(
                        Employee.full_name.ilike(like_query),
                        Employee.employee_ref.ilike(like_query),
                        Person.first_name.ilike(like_query),
                        Person.last_name.ilike(like_query),
                        Person.document_number.ilike(like_query),
                    )
                )

        if sort not in VALID_SORT_FIELDS:
            raise BadRequest("invalid_sort")

        if order not in VALID_ORDERS:
            raise BadRequest("invalid_order")

        sort_column = SORT_FIELD_MAP[sort]
        direction = sort_column.asc() if order == "asc" else sort_column.desc()
        fallback_direction = Employee.created_at.asc() if order == "asc" else Employee.created_at.desc()

        total_count = query.count()
        rows = (
            query.order_by(direction, fallback_direction)
            .limit(max(limit, 1))
            .offset(max(offset, 0))
            .all()
        )
        return [self._hydrate_row(row) for row in rows], total_count

    def _base_enriched_query(self, client_id: str):
        return (
            self.session.query(Employee, Person, PersonCompanyRelation)
            .outerjoin(Person, and_(Person.id == Employee.person_id, Person.client_id == client_id))
            .outerjoin(
                PersonCompanyRelation,
                and_(
                    PersonCompanyRelation.person_id == Employee.person_id,
                    PersonCompanyRelation.company_id == Employee.company_id,
                    PersonCompanyRelation.client_id == Employee.client_id,
                    PersonCompanyRelation.relation_type == "employee",
                    PersonCompanyRelation.status == "active",
                ),
            )
        )

    @staticmethod
    def _hydrate_row(row: tuple[Employee, Person | None, PersonCompanyRelation | None] | None) -> Employee | None:
        if row is None:
            return None
        employee, person, relation = row
        employee.person_full_name = None
        employee.person_document_number = None
        employee.person_relation_type = None
        employee.person_relation_status = None
        if person is not None:
            employee.person_full_name = f"{person.first_name} {person.last_name}".strip()
            employee.person_document_number = person.document_number
        if relation is not None:
            employee.person_relation_type = relation.relation_type
            employee.person_relation_status = relation.status
        return employee
