"""Repository for person data access."""

from __future__ import annotations

from sqlalchemy import or_

from app.extensions import db
from app.models.person import Person


class PersonRepository:
    """Data access layer for Person."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def create_person(self, person: Person) -> Person:
        self.session.add(person)
        self.session.flush()
        return person

    def get_person_by_id(self, person_id: str, client_id: str) -> Person | None:
        return (
            self.session.query(Person)
            .filter(Person.id == person_id, Person.client_id == client_id)
            .one_or_none()
        )

    def list_persons(
        self,
        client_id: str,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Person], int]:
        query = self.session.query(Person).filter(Person.client_id == client_id)
        if status:
            query = query.filter(Person.status == status)

        total = query.count()
        items = (
            query.order_by(Person.created_at.desc())
            .offset(max(page - 1, 0) * max(limit, 1))
            .limit(max(limit, 1))
            .all()
        )
        return items, total

    def update_person(self, person: Person) -> Person:
        self.session.add(person)
        self.session.flush()
        return person

    def search_persons(
        self,
        client_id: str,
        search: str,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Person], int]:
        query = self.session.query(Person).filter(Person.client_id == client_id)
        if status:
            query = query.filter(Person.status == status)

        q = (search or "").strip()
        if q:
            like = f"%{q}%"
            query = query.filter(
                or_(
                    Person.first_name.ilike(like),
                    Person.last_name.ilike(like),
                    Person.document_number.ilike(like),
                    Person.email.ilike(like),
                )
            )

        total = query.count()
        items = (
            query.order_by(Person.created_at.desc())
            .offset(max(page - 1, 0) * max(limit, 1))
            .limit(max(limit, 1))
            .all()
        )
        return items, total

    def get_by_document_number(self, client_id: str, document_number: str) -> Person | None:
        return (
            self.session.query(Person)
            .filter(Person.client_id == client_id, Person.document_number == document_number)
            .one_or_none()
        )
