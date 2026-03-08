"""Repository for case and case event data access."""

from __future__ import annotations

from sqlalchemy import or_
from werkzeug.exceptions import BadRequest

from app.extensions import db
from app.models.case import Case
from app.models.case_event import CaseEvent

VALID_SORT_FIELDS = {"due_date", "created_at", "status", "title"}
VALID_ORDERS = {"asc", "desc"}


class CaseRepository:
    """Data access layer for Case."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def create(self, case: Case) -> Case:
        self.session.add(case)
        self.session.flush()
        return case

    def get_by_id(self, case_id: str, client_id: str) -> Case | None:
        return (
            self.session.query(Case)
            .filter(Case.id == case_id, Case.client_id == client_id)
            .one_or_none()
        )

    def list_cases(
        self,
        client_id: str,
        company_id: str | None = None,
        person_id: str | None = None,
        status: str | None = None,
        case_type: str | None = None,
        q: str | None = None,
        allowed_company_ids: set[str] | None = None,
        sort: str | None = None,
        order: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Case]:
        query = self.session.query(Case).filter(Case.client_id == client_id)

        if allowed_company_ids is not None:
            if not allowed_company_ids:
                query = query.filter(Case.company_id.is_(None))
            else:
                query = query.filter(or_(Case.company_id.is_(None), Case.company_id.in_(allowed_company_ids)))

        if company_id is not None:
            query = query.filter(Case.company_id == company_id)

        if person_id is not None:
            query = query.filter(Case.person_id == person_id)

        if status is not None:
            query = query.filter(Case.status == status)

        if case_type is not None:
            query = query.filter(Case.type == case_type)

        if q is not None:
            q_value = q.strip()
            if q_value:
                like_value = f"%{q_value}%"
                query = query.filter(
                    or_(
                        Case.title.ilike(like_value),
                        Case.description.ilike(like_value),
                    )
                )

        sort_value = sort or "created_at"
        if sort_value not in VALID_SORT_FIELDS:
            raise BadRequest("invalid_sort")

        order_value = order or "desc"
        if order_value not in VALID_ORDERS:
            raise BadRequest("invalid_order")

        sort_column = getattr(Case, sort_value)
        direction = sort_column.asc() if order_value == "asc" else sort_column.desc()
        fallback_direction = Case.created_at.asc() if order_value == "asc" else Case.created_at.desc()

        return (
            query.order_by(direction, fallback_direction)
            .limit(max(limit, 1))
            .offset(max(offset, 0))
            .all()
        )

    def update(self, case: Case) -> Case:
        self.session.add(case)
        self.session.flush()
        return case


class CaseEventRepository:
    """Data access layer for CaseEvent."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def create(self, event: CaseEvent) -> CaseEvent:
        self.session.add(event)
        self.session.flush()
        return event

    def list_by_case(
        self,
        case_id: str,
        client_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CaseEvent]:
        return (
            self.session.query(CaseEvent)
            .filter(CaseEvent.case_id == case_id, CaseEvent.client_id == client_id)
            .order_by(CaseEvent.created_at.desc())
            .limit(max(limit, 1))
            .offset(max(offset, 0))
            .all()
        )
