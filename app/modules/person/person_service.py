"""Service layer for person operations."""

from __future__ import annotations

from werkzeug.exceptions import BadRequest, NotFound

from app.models.person import Person
from app.modules.audit.audit_service import AuditService
from app.modules.person.person_repository import PersonRepository
from app.modules.person.person_schemas import PersonCreateRequest, PersonUpdateRequest


class PersonService:
    """Business logic for person operations."""

    def __init__(
        self,
        repository: PersonRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.repository = repository or PersonRepository()
        self.audit_service = audit_service or AuditService()

    def create_person(self, client_id: str, user_id: str | None, payload: PersonCreateRequest) -> Person:
        self._ensure_document_unique(client_id, payload.document_number)
        person = Person(
            client_id=client_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            document_type=payload.document_type,
            document_number=payload.document_number,
            email=payload.email,
            phone=payload.phone,
            birth_date=payload.birth_date,
            address_line1=payload.address_line1,
            address_line2=payload.address_line2,
            city=payload.city,
            postal_code=payload.postal_code,
            country=payload.country,
            status=payload.status,
            created_by=user_id,
        )
        self.repository.create_person(person)
        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=user_id,
            action="person.created",
            entity_type="person",
            entity_id=person.id,
            metadata={"status": person.status, "document_number": person.document_number},
        )
        return person

    def update_person(
        self,
        client_id: str,
        user_id: str | None,
        person_id: str,
        payload: PersonUpdateRequest,
    ) -> Person:
        person = self.get_person(client_id, person_id)
        previous_status = person.status

        if payload.document_number is not None and payload.document_number != person.document_number:
            self._ensure_document_unique(client_id, payload.document_number)
            person.document_number = payload.document_number

        for field in (
            "first_name",
            "last_name",
            "document_type",
            "email",
            "phone",
            "birth_date",
            "address_line1",
            "address_line2",
            "city",
            "postal_code",
            "country",
            "status",
        ):
            value = getattr(payload, field)
            if value is not None:
                setattr(person, field, value)

        self.repository.update_person(person)
        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=user_id,
            action="person.updated",
            entity_type="person",
            entity_id=person.id,
            metadata={"status": person.status},
        )
        if previous_status != person.status:
            self.audit_service.log_action(
                client_id=client_id,
                actor_user_id=user_id,
                action="person.status_changed",
                entity_type="person",
                entity_id=person.id,
                metadata={"from": previous_status, "to": person.status},
            )
        return person

    def get_person(self, client_id: str, person_id: str) -> Person:
        person = self.repository.get_person_by_id(person_id, client_id)
        if person is None:
            raise NotFound("Person not found.")
        return person

    def list_persons(
        self,
        client_id: str,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Person], int]:
        return self.repository.list_persons(client_id=client_id, status=status, page=page, limit=limit)

    def search_persons(
        self,
        client_id: str,
        search: str,
        status: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Person], int]:
        return self.repository.search_persons(
            client_id=client_id,
            search=search,
            status=status,
            page=page,
            limit=limit,
        )

    def _ensure_document_unique(self, client_id: str, document_number: str) -> None:
        existing = self.repository.get_by_document_number(client_id, document_number)
        if existing:
            raise BadRequest("duplicate_document_number")
