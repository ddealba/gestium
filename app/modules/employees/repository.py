"""Repository for employee data access."""

from __future__ import annotations

from werkzeug.exceptions import BadRequest
from sqlalchemy import or_

from app.extensions import db
from app.models.employee import Employee

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
        return (
            self.session.query(Employee)
            .filter(Employee.id == employee_id, Employee.client_id == client_id)
            .one_or_none()
        )

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
        query = self.session.query(Employee).filter(
            Employee.company_id == company_id,
            Employee.client_id == client_id,
        )

        if status:
            query = query.filter(Employee.status == status)

        if q is not None:
            q_value = q.strip()
            if q_value:
                like_query = f"%{q_value}%"
                query = query.filter(or_(Employee.full_name.ilike(like_query), Employee.employee_ref.ilike(like_query)))

        if sort not in VALID_SORT_FIELDS:
            raise BadRequest("invalid_sort")

        if order not in VALID_ORDERS:
            raise BadRequest("invalid_order")

        sort_column = SORT_FIELD_MAP[sort]
        direction = sort_column.asc() if order == "asc" else sort_column.desc()
        fallback_direction = Employee.created_at.asc() if order == "asc" else Employee.created_at.desc()

        total_count = query.count()
        items = (
            query.order_by(direction, fallback_direction)
            .limit(max(limit, 1))
            .offset(max(offset, 0))
            .all()
        )
        return items, total_count
