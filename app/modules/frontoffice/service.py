"""Frontoffice service layer."""

from __future__ import annotations

from sqlalchemy import or_, select
from werkzeug.exceptions import Forbidden, NotFound

from app.extensions import db
from app.models.case import Case
from app.models.document import Document
from app.models.employee import Employee
from app.models.person import Person
from app.models.person_company_relation import PersonCompanyRelation
from app.modules.frontoffice.schemas import (
    serialize_case,
    serialize_company_relation,
    serialize_document,
    serialize_profile,
)


class FrontofficeService:
    """Provides person-scoped frontoffice reads."""

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

    def get_portal_documents(self, user, client_id: str) -> list[dict]:
        person_id = self._ensure_person_id(user)
        employee_ids_subq = select(Employee.id).where(
            Employee.client_id == client_id,
            Employee.person_id == person_id,
        )
        rows = (
            db.session.query(Document)
            .filter(
                Document.client_id == client_id,
                or_(
                    Document.person_id == person_id,
                    Document.employee_id.in_(employee_ids_subq),
                ),
            )
            .order_by(Document.created_at.desc())
            .all()
        )
        return [serialize_document(item) for item in rows]

    def get_portal_cases(self, user, client_id: str) -> list[dict]:
        person_id = self._ensure_person_id(user)
        rows = (
            db.session.query(Case)
            .filter(Case.client_id == client_id, Case.person_id == person_id)
            .order_by(Case.created_at.desc())
            .all()
        )
        return [serialize_case(item) for item in rows]

    def get_portal_companies(self, user, client_id: str) -> list[dict]:
        person_id = self._ensure_person_id(user)
        rows = (
            db.session.query(PersonCompanyRelation)
            .filter(
                PersonCompanyRelation.client_id == client_id,
                PersonCompanyRelation.person_id == person_id,
            )
            .order_by(PersonCompanyRelation.created_at.desc())
            .all()
        )
        return [serialize_company_relation(item) for item in rows]
