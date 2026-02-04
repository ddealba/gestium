"""Service layer for case operations."""

from __future__ import annotations

from app.models.case import Case
from app.repositories.case_repository import CaseRepository


class CaseService:
    """Case service for CRUD operations."""

    def __init__(self, repository: CaseRepository | None = None) -> None:
        self.repository = repository or CaseRepository()

    def create_case(self, client_id: str, company_id: str, title: str) -> Case:
        case = Case(client_id=client_id, company_id=company_id, title=title)
        return self.repository.add(case)
