"""Repository for case data access."""

from __future__ import annotations

from sqlalchemy import false

from app.extensions import db
from app.models.case import Case


class CaseRepository:
    """Data access layer for Case."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def add(self, case: Case) -> Case:
        self.session.add(case)
        self.session.flush()
        return case

    @staticmethod
    def filter_by_allowed_companies(query, allowed_company_ids: set[str]):
        if not allowed_company_ids:
            return query.filter(false())
        return query.filter(Case.company_id.in_(allowed_company_ids))
