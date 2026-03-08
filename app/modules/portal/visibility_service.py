"""Portal visibility rules based on person roles and relations."""

from __future__ import annotations

from sqlalchemy import or_

from app.extensions import db
from app.models.case import Case
from app.models.document import Document
from app.models.employee import Employee
from app.models.person_company_relation import PersonCompanyRelation


class PortalVisibilityService:
    """Resolve visible records for a portal person user."""

    def get_portal_visible_company_ids(self, person_id: str, client_id: str) -> list[str]:
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

    def get_portal_visible_employee_ids(self, person_id: str, client_id: str) -> list[str]:
        rows = (
            db.session.query(Employee.id)
            .filter(Employee.client_id == client_id, Employee.person_id == person_id)
            .all()
        )
        return [employee_id for (employee_id,) in rows]

    def get_portal_documents(
        self,
        person_id: str,
        client_id: str,
        section: str | None = None,
    ) -> list[Document]:
        employee_ids = self.get_portal_visible_employee_ids(person_id, client_id)
        owner_company_ids = self.get_portal_visible_company_ids(person_id, client_id)

        query = db.session.query(Document).filter(Document.client_id == client_id)

        if section == "person":
            query = query.filter(Document.person_id == person_id)
        elif section == "employee":
            if not employee_ids:
                return []
            query = query.filter(Document.employee_id.in_(employee_ids))
        elif section == "company":
            if not owner_company_ids:
                return []
            query = query.filter(Document.company_id.in_(owner_company_ids))
        else:
            clauses = [Document.person_id == person_id]
            if employee_ids:
                clauses.append(Document.employee_id.in_(employee_ids))
            if owner_company_ids:
                clauses.append(Document.company_id.in_(owner_company_ids))
            query = query.filter(or_(*clauses))

        return query.order_by(Document.created_at.desc()).all()

    def get_portal_cases(
        self,
        person_id: str,
        client_id: str,
        section: str | None = None,
    ) -> list[Case]:
        owner_company_ids = self.get_portal_visible_company_ids(person_id, client_id)
        query = db.session.query(Case).filter(Case.client_id == client_id)

        if section == "person":
            query = query.filter(Case.person_id == person_id)
        elif section == "company":
            if not owner_company_ids:
                return []
            query = query.filter(Case.company_id.in_(owner_company_ids))
        else:
            clauses = [Case.person_id == person_id]
            if owner_company_ids:
                clauses.append(Case.company_id.in_(owner_company_ids))
            query = query.filter(or_(*clauses))

        return query.order_by(Case.created_at.desc()).all()

    def company_is_visible(self, person_id: str, client_id: str, company_id: str) -> bool:
        visible_company_ids = self.get_portal_visible_company_ids(person_id, client_id)
        return company_id in set(visible_company_ids)
