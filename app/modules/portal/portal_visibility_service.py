"""Portal visibility rules based on person roles and relations."""

from __future__ import annotations

from sqlalchemy import func, or_

from app.extensions import db
from app.models.case import Case
from app.models.document import Document
from app.models.employee import Employee
from app.models.person_company_relation import PersonCompanyRelation
from app.models.person_request import PersonRequest


class PortalVisibilityService:
    """Resolve visible records for a portal person user."""

    def get_visible_companies(self, person_id: str, client_id: str) -> list[PersonCompanyRelation]:
        return (
            db.session.query(PersonCompanyRelation)
            .filter(
                PersonCompanyRelation.client_id == client_id,
                PersonCompanyRelation.person_id == person_id,
                PersonCompanyRelation.relation_type == "owner",
                PersonCompanyRelation.status == "active",
            )
            .order_by(PersonCompanyRelation.created_at.desc())
            .all()
        )

    def get_visible_company_ids(self, person_id: str, client_id: str) -> list[str]:
        rows = (
            db.session.query(PersonCompanyRelation.company_id)
            .filter(
                PersonCompanyRelation.client_id == client_id,
                PersonCompanyRelation.person_id == person_id,
                PersonCompanyRelation.relation_type == "owner",
                PersonCompanyRelation.status == "active",
            )
            .all()
        )
        return [company_id for (company_id,) in rows]

    def get_visible_employee_ids(self, person_id: str, client_id: str) -> list[str]:
        rows = (
            db.session.query(Employee.id)
            .filter(Employee.client_id == client_id, Employee.person_id == person_id)
            .all()
        )
        return [employee_id for (employee_id,) in rows]

    def _documents_query(self, person_id: str, client_id: str, scope: str | None = None):
        employee_ids = self.get_visible_employee_ids(person_id, client_id)
        company_ids = self.get_visible_company_ids(person_id, client_id)
        query = db.session.query(Document).filter(Document.client_id == client_id)

        if scope == "person":
            return query.filter(Document.person_id == person_id)
        if scope == "employee":
            return query.filter(Document.employee_id.in_(employee_ids)) if employee_ids else query.filter(False)
        if scope == "company":
            return query.filter(Document.company_id.in_(company_ids)) if company_ids else query.filter(False)

        clauses = [Document.person_id == person_id]
        if employee_ids:
            clauses.append(Document.employee_id.in_(employee_ids))
        if company_ids:
            clauses.append(Document.company_id.in_(company_ids))
        return query.filter(or_(*clauses))

    def get_visible_documents(self, person_id: str, client_id: str, scope: str | None = None) -> list[Document]:
        return self._documents_query(person_id, client_id, scope).order_by(Document.created_at.desc()).all()

    def count_visible_documents(self, person_id: str, client_id: str, scope: str | None = None) -> int:
        query = self._documents_query(person_id, client_id, scope).with_entities(func.count(Document.id))
        return int(query.scalar() or 0)

    def _cases_query(self, person_id: str, client_id: str, scope: str | None = None):
        company_ids = self.get_visible_company_ids(person_id, client_id)
        query = db.session.query(Case).filter(Case.client_id == client_id)

        if scope == "person":
            return query.filter(Case.person_id == person_id)
        if scope == "company":
            return query.filter(Case.company_id.in_(company_ids)) if company_ids else query.filter(False)

        clauses = [Case.person_id == person_id]
        if company_ids:
            clauses.append(Case.company_id.in_(company_ids))
        return query.filter(or_(*clauses))

    def get_visible_cases(self, person_id: str, client_id: str, scope: str | None = None) -> list[Case]:
        return self._cases_query(person_id, client_id, scope).order_by(Case.created_at.desc()).all()

    def count_visible_cases(self, person_id: str, client_id: str, scope: str | None = None) -> int:
        query = self._cases_query(person_id, client_id, scope).with_entities(func.count(Case.id))
        return int(query.scalar() or 0)



    def count_recent_visible_documents(self, person_id: str, client_id: str, since) -> int:
        query = self._documents_query(person_id, client_id).with_entities(func.count(Document.id)).filter(Document.created_at >= since)
        return int(query.scalar() or 0)

    def count_open_visible_cases(self, person_id: str, client_id: str) -> int:
        closed_statuses = {"closed", "resolved", "cancelled", "done"}
        query = self._cases_query(person_id, client_id).with_entities(func.count(Case.id)).filter(~Case.status.in_(closed_statuses))
        return int(query.scalar() or 0)

    def get_visible_requests(self, person_id: str, client_id: str) -> list[PersonRequest]:
        return (
            db.session.query(PersonRequest)
            .filter(PersonRequest.client_id == client_id, PersonRequest.person_id == person_id)
            .order_by(PersonRequest.created_at.desc())
            .all()
        )

    def count_pending_requests(self, person_id: str, client_id: str) -> int:
        actionable_statuses = {"pending", "submitted", "in_review", "rejected", "expired"}
        query = (
            db.session.query(func.count(PersonRequest.id))
            .filter(
                PersonRequest.client_id == client_id,
                PersonRequest.person_id == person_id,
                PersonRequest.status.in_(actionable_statuses),
            )
        )
        return int(query.scalar() or 0)

    def count_visible_companies(self, person_id: str, client_id: str) -> int:
        query = (
            db.session.query(func.count(PersonCompanyRelation.company_id))
            .filter(
                PersonCompanyRelation.client_id == client_id,
                PersonCompanyRelation.person_id == person_id,
                PersonCompanyRelation.relation_type == "owner",
                PersonCompanyRelation.status == "active",
            )
        )
        return int(query.scalar() or 0)

    def company_is_visible(self, person_id: str, client_id: str, company_id: str) -> bool:
        return company_id in set(self.get_visible_company_ids(person_id, client_id))

    # Backward compatibility with previous frontoffice service API.
    def get_portal_visible_company_ids(self, person_id: str, client_id: str) -> list[str]:
        return self.get_visible_company_ids(person_id, client_id)

    def get_portal_visible_employee_ids(self, person_id: str, client_id: str) -> list[str]:
        return self.get_visible_employee_ids(person_id, client_id)

    def get_portal_documents(self, person_id: str, client_id: str, section: str | None = None) -> list[Document]:
        return self.get_visible_documents(person_id, client_id, scope=section)

    def get_portal_cases(self, person_id: str, client_id: str, section: str | None = None) -> list[Case]:
        return self.get_visible_cases(person_id, client_id, scope=section)
