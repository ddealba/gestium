"""Repository for person-company relations."""

from __future__ import annotations

from sqlalchemy import and_

from app.extensions import db
from app.models.company import Company
from app.models.person import Person
from app.models.person_company_relation import PersonCompanyRelation


class PersonCompanyRelationRepository:
    """Data access layer for person-company relations."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def create_relation(self, relation: PersonCompanyRelation) -> PersonCompanyRelation:
        self.session.add(relation)
        self.session.flush()
        return relation

    def get_relation_by_id(self, relation_id: str, client_id: str) -> PersonCompanyRelation | None:
        return (
            self.session.query(PersonCompanyRelation)
            .filter(PersonCompanyRelation.id == relation_id, PersonCompanyRelation.client_id == client_id)
            .one_or_none()
        )

    def list_relations_by_person(self, person_id: str, client_id: str) -> list[tuple[PersonCompanyRelation, Company]]:
        return (
            self.session.query(PersonCompanyRelation, Company)
            .join(Company, and_(Company.id == PersonCompanyRelation.company_id, Company.client_id == client_id))
            .filter(PersonCompanyRelation.client_id == client_id, PersonCompanyRelation.person_id == person_id)
            .order_by(PersonCompanyRelation.created_at.desc())
            .all()
        )

    def list_relations_by_company(self, company_id: str, client_id: str) -> list[tuple[PersonCompanyRelation, Person]]:
        return (
            self.session.query(PersonCompanyRelation, Person)
            .join(Person, and_(Person.id == PersonCompanyRelation.person_id, Person.client_id == client_id))
            .filter(PersonCompanyRelation.client_id == client_id, PersonCompanyRelation.company_id == company_id)
            .order_by(PersonCompanyRelation.created_at.desc())
            .all()
        )

    def find_active_relation(
        self,
        client_id: str,
        person_id: str,
        company_id: str,
        relation_type: str,
    ) -> PersonCompanyRelation | None:
        return (
            self.session.query(PersonCompanyRelation)
            .filter(
                PersonCompanyRelation.client_id == client_id,
                PersonCompanyRelation.person_id == person_id,
                PersonCompanyRelation.company_id == company_id,
                PersonCompanyRelation.relation_type == relation_type,
                PersonCompanyRelation.status == "active",
            )
            .one_or_none()
        )

    def update_relation(self, relation: PersonCompanyRelation) -> PersonCompanyRelation:
        self.session.add(relation)
        self.session.flush()
        return relation

    def deactivate_relation(self, relation: PersonCompanyRelation) -> PersonCompanyRelation:
        relation.status = "inactive"
        self.session.add(relation)
        self.session.flush()
        return relation
