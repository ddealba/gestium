"""Service layer for person-company relations."""

from __future__ import annotations

from werkzeug.exceptions import BadRequest, NotFound

from app.models.person_company_relation import PersonCompanyRelation
from app.modules.audit.audit_service import AuditService
from app.modules.companies.repository import CompanyRepository
from app.modules.person.person_repository import PersonRepository
from app.modules.person_company_relation.relation_repository import PersonCompanyRelationRepository
from app.modules.person_company_relation.relation_schemas import (
    PersonCompanyRelationCreateRequest,
    PersonCompanyRelationUpdateRequest,
)


class PersonCompanyRelationService:
    """Business logic for person-company relations."""

    def __init__(
        self,
        repository: PersonCompanyRelationRepository | None = None,
        person_repository: PersonRepository | None = None,
        company_repository: CompanyRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self.repository = repository or PersonCompanyRelationRepository()
        self.person_repository = person_repository or PersonRepository()
        self.company_repository = company_repository or CompanyRepository()
        self.audit_service = audit_service or AuditService()

    def create_person_company_relation(
        self,
        client_id: str,
        user_id: str | None,
        person_id: str,
        payload: PersonCompanyRelationCreateRequest,
    ) -> PersonCompanyRelation:
        self._ensure_person_company_same_tenant(client_id, person_id, payload.company_id)
        self._validate_dates(payload.start_date, payload.end_date)

        existing = self.repository.find_active_relation(
            client_id=client_id,
            person_id=person_id,
            company_id=payload.company_id,
            relation_type=payload.relation_type,
        )
        if existing and payload.status == "active":
            raise BadRequest("duplicate_active_relation")

        relation = PersonCompanyRelation(
            client_id=client_id,
            person_id=person_id,
            company_id=payload.company_id,
            relation_type=payload.relation_type,
            status=payload.status,
            start_date=payload.start_date,
            end_date=payload.end_date,
            notes=payload.notes,
            created_by=user_id,
        )
        self.repository.create_relation(relation)
        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=user_id,
            action="person_company_relation_created",
            entity_type="person_company_relation",
            entity_id=relation.id,
            metadata={
                "person_id": relation.person_id,
                "company_id": relation.company_id,
                "relation_type": relation.relation_type,
                "status": relation.status,
            },
        )
        return relation

    def get_person_relations(self, client_id: str, person_id: str) -> list[dict]:
        person = self.person_repository.get_person_by_id(person_id, client_id)
        if person is None:
            raise NotFound("Person not found.")
        rows = self.repository.list_relations_by_person(person_id, client_id)
        return [
            {
                "relation_id": relation.id,
                "company_id": company.id,
                "company_name": company.name,
                "relation_type": relation.relation_type,
                "status": relation.status,
                "start_date": relation.start_date.isoformat() if relation.start_date else None,
                "end_date": relation.end_date.isoformat() if relation.end_date else None,
                "notes": relation.notes,
            }
            for relation, company in rows
        ]

    def get_company_relations(self, client_id: str, company_id: str) -> list[dict]:
        company = self.company_repository.get_by_id(company_id, client_id)
        if company is None:
            raise NotFound("Company not found.")
        rows = self.repository.list_relations_by_company(company_id, client_id)
        return [
            {
                "relation_id": relation.id,
                "person_id": person.id,
                "full_name": f"{person.first_name} {person.last_name}".strip(),
                "document_number": person.document_number,
                "relation_type": relation.relation_type,
                "status": relation.status,
                "start_date": relation.start_date.isoformat() if relation.start_date else None,
                "end_date": relation.end_date.isoformat() if relation.end_date else None,
                "notes": relation.notes,
            }
            for relation, person in rows
        ]

    def update_person_company_relation(
        self,
        client_id: str,
        user_id: str | None,
        relation_id: str,
        payload: PersonCompanyRelationUpdateRequest,
    ) -> PersonCompanyRelation:
        relation = self._get_relation(client_id, relation_id)

        relation_type = payload.relation_type or relation.relation_type
        status = payload.status or relation.status
        start_date = payload.start_date or relation.start_date
        end_date = payload.end_date if payload.end_date is not None else relation.end_date

        self._validate_dates(start_date, end_date)
        if status == "active":
            duplicate = self.repository.find_active_relation(
                client_id=client_id,
                person_id=relation.person_id,
                company_id=relation.company_id,
                relation_type=relation_type,
            )
            if duplicate is not None and duplicate.id != relation.id:
                raise BadRequest("duplicate_active_relation")

        if payload.relation_type is not None:
            relation.relation_type = payload.relation_type
        if payload.status is not None:
            relation.status = payload.status
        if payload.start_date is not None:
            relation.start_date = payload.start_date
        if payload.end_date is not None:
            relation.end_date = payload.end_date
        if payload.notes is not None:
            relation.notes = payload.notes

        self.repository.update_relation(relation)
        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=user_id,
            action="person_company_relation_updated",
            entity_type="person_company_relation",
            entity_id=relation.id,
            metadata={"status": relation.status, "relation_type": relation.relation_type},
        )
        return relation

    def deactivate_person_company_relation(
        self,
        client_id: str,
        user_id: str | None,
        relation_id: str,
    ) -> PersonCompanyRelation:
        relation = self._get_relation(client_id, relation_id)
        self.repository.deactivate_relation(relation)
        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=user_id,
            action="person_company_relation_deactivated",
            entity_type="person_company_relation",
            entity_id=relation.id,
            metadata={"person_id": relation.person_id, "company_id": relation.company_id},
        )
        return relation

    def _get_relation(self, client_id: str, relation_id: str) -> PersonCompanyRelation:
        relation = self.repository.get_relation_by_id(relation_id, client_id)
        if relation is None:
            raise NotFound("Person-company relation not found.")
        return relation

    def _ensure_person_company_same_tenant(self, client_id: str, person_id: str, company_id: str) -> None:
        person = self.person_repository.get_person_by_id(person_id, client_id)
        if person is None:
            raise NotFound("Person not found.")
        company = self.company_repository.get_by_id(company_id, client_id)
        if company is None:
            raise NotFound("Company not found.")

    def _validate_dates(self, start_date, end_date) -> None:
        if end_date is not None and end_date < start_date:
            raise BadRequest("invalid_date_range")
