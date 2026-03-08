"""Frontoffice service layer."""

from __future__ import annotations

from werkzeug.exceptions import Forbidden, NotFound

from app.extensions import db
from app.models.company import Company
from app.models.person import Person
from app.models.person_company_relation import PersonCompanyRelation
from app.modules.frontoffice.schemas import (
    serialize_case,
    serialize_company_relation,
    serialize_document,
    serialize_profile,
)
from app.modules.portal.visibility_service import PortalVisibilityService


class FrontofficeService:
    """Provides person-scoped frontoffice reads."""

    def __init__(self) -> None:
        self.visibility = PortalVisibilityService()

    @staticmethod
    def _ensure_person_id(user) -> str:
        if not user.person_id:
            raise Forbidden("portal_user_requires_person")
        return str(user.person_id)

    def get_portal_profile(self, user, client_id: str) -> dict:
        person_id = self._ensure_person_id(user)
        person = (
            db.session.query(Person)
            .filter(Person.id == person_id, Person.client_id == client_id)
            .one_or_none()
        )
        if person is None:
            raise NotFound("person_not_found")
        return serialize_profile(person)

    def get_portal_documents(self, user, client_id: str, section: str | None = None) -> list[dict]:
        person_id = self._ensure_person_id(user)
        rows = self.visibility.get_portal_documents(person_id, client_id, section)
        return [serialize_document(item, section) for item in rows]

    def get_portal_cases(self, user, client_id: str, section: str | None = None) -> list[dict]:
        person_id = self._ensure_person_id(user)
        rows = self.visibility.get_portal_cases(person_id, client_id, section)
        return [serialize_case(item, section) for item in rows]

    def get_portal_companies(self, user, client_id: str) -> list[dict]:
        person_id = self._ensure_person_id(user)
        rows = (
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
        return [serialize_company_relation(item) for item in rows]

    def get_portal_company_detail(self, user, client_id: str, company_id: str) -> dict:
        person_id = self._ensure_person_id(user)
        if not self.visibility.company_is_visible(person_id, client_id, company_id):
            raise Forbidden("portal_company_forbidden")

        company = (
            db.session.query(Company)
            .filter(Company.id == company_id, Company.client_id == client_id)
            .one_or_none()
        )
        if company is None:
            raise NotFound("company_not_found")

        return {
            "company_id": company.id,
            "name": company.name,
            "tax_id": company.tax_id,
            "status": company.status,
        }

    def get_portal_summary(self, user, client_id: str) -> dict:
        person_docs = self.get_portal_documents(user, client_id, section="person")
        employee_docs = self.get_portal_documents(user, client_id, section="employee")
        company_docs = self.get_portal_documents(user, client_id, section="company")
        person_cases = self.get_portal_cases(user, client_id, section="person")
        company_cases = self.get_portal_cases(user, client_id, section="company")
        companies = self.get_portal_companies(user, client_id)

        return {
            "person_documents": len(person_docs),
            "employee_documents": len(employee_docs),
            "company_documents": len(company_docs),
            "personal_cases": len(person_cases),
            "company_cases": len(company_cases),
            "companies_count": len(companies),
            "has_employee_scope": len(employee_docs) > 0,
            "has_company_scope": len(companies) > 0,
        }
