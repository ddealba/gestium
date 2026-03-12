"""Person completeness and onboarding orchestration."""

from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db
from app.models.document import Document
from app.models.person import Person
from app.models.person_request import PersonRequest
from app.models.user import User
from app.modules.audit.audit_service import AuditService

REQUIRED_PERSON_DOCUMENT_TYPES = ("dni",)
ACTIVE_REQUEST_STATUSES = {"pending", "submitted", "in_review", "rejected", "expired"}


class PersonCompletenessService:
    """Evaluate person onboarding completeness and automate follow-up requests."""

    REQUIRED_FIELDS = {
        "basic_info": ("first_name", "last_name"),
        "identification": ("document_type", "document_number"),
        "contact_info": ("email", "phone"),
        "address_info": ("address_line1", "city", "postal_code", "country"),
    }

    def __init__(self, audit_service: AuditService | None = None) -> None:
        self.session = db.session
        self.audit_service = audit_service or AuditService()

    def get_person_completeness(self, person_id: str, client_id: str) -> dict:
        person = self._get_person(person_id, client_id)
        checks, missing_fields = self._evaluate_field_checks(person)
        checks["portal_access"] = self._has_portal_access(person.id, client_id)
        missing_documents = self.get_missing_documents(person_id, client_id)
        checks["required_documents"] = len(missing_documents) == 0

        completion_pct = int(round((sum(1 for value in checks.values() if value) / len(checks)) * 100)) if checks else 0
        status = self.get_onboarding_status(person_id, client_id, checks=checks, completion_pct=completion_pct)

        return {
            "completion_pct": completion_pct,
            "status": status,
            "checks": checks,
            "missing_fields": missing_fields,
            "missing_documents": missing_documents,
        }

    def get_missing_fields(self, person_id: str, client_id: str) -> list[str]:
        person = self._get_person(person_id, client_id)
        _, missing_fields = self._evaluate_field_checks(person)
        return missing_fields

    def get_missing_documents(self, person_id: str, client_id: str) -> list[str]:
        self._get_person(person_id, client_id)
        present_types = {
            (item.doc_type or "").strip().lower()
            for item in self.session.query(Document).filter(
                Document.client_id == client_id,
                Document.person_id == person_id,
                Document.status != "archived",
            )
        }
        return [doc_type for doc_type in REQUIRED_PERSON_DOCUMENT_TYPES if doc_type not in present_types]

    def get_onboarding_status(
        self,
        person_id: str,
        client_id: str,
        checks: dict[str, bool] | None = None,
        completion_pct: int | None = None,
    ) -> str:
        person = self._get_person(person_id, client_id)
        if person.status == "inactive":
            return "inactive"

        resolved_checks = checks
        resolved_completion_pct = completion_pct
        if resolved_checks is None or resolved_completion_pct is None:
            completeness = self.get_person_completeness(person_id, client_id)
            resolved_checks = completeness["checks"]
            resolved_completion_pct = completeness["completion_pct"]

        if all(resolved_checks.values()):
            return "active"
        if resolved_completion_pct <= 25:
            return "draft"
        return "pending_info"

    def recalculate_person_status(self, person: Person, actor_user_id: str | None = None) -> dict:
        completeness = self.get_person_completeness(person.id, person.client_id)
        previous_status = person.status
        if person.status != "inactive":
            person.status = completeness["status"]

        self.audit_service.log_action(
            client_id=person.client_id,
            actor_user_id=actor_user_id,
            action="person_completeness_recalculated",
            entity_type="person",
            entity_id=person.id,
            metadata={"completion_pct": completeness["completion_pct"], "status": completeness["status"]},
        )
        if previous_status != person.status:
            self.audit_service.log_action(
                client_id=person.client_id,
                actor_user_id=actor_user_id,
                action="person_status_changed_auto",
                entity_type="person",
                entity_id=person.id,
                metadata={"from": previous_status, "to": person.status},
            )
        return completeness

    def generate_pending_requests(
        self,
        client_id: str,
        person_id: str,
        actor_user_id: str | None = None,
        force_regenerate: bool = False,
    ) -> list[PersonRequest]:
        completeness = self.get_person_completeness(person_id, client_id)
        existing_requests = (
            self.session.query(PersonRequest)
            .filter(PersonRequest.client_id == client_id, PersonRequest.person_id == person_id)
            .order_by(PersonRequest.created_at.desc())
            .all()
        )

        created: list[PersonRequest] = []
        for field in completeness["missing_fields"]:
            need_key = f"field:{field}"
            if self._should_skip_request(existing_requests, need_key, force_regenerate):
                continue
            title = self._field_request_title(field)
            created_item = PersonRequest(
                client_id=client_id,
                person_id=person_id,
                request_type="complete_profile",
                title=title,
                description=f"Necesitamos que completes el campo: {field}.",
                status="pending",
                resolution_type="form_submission",
                created_by=actor_user_id,
                resolution_payload={"auto_need_key": need_key, "field": field},
            )
            self.session.add(created_item)
            existing_requests.insert(0, created_item)
            created.append(created_item)

        for doc_type in completeness["missing_documents"]:
            need_key = f"document:{doc_type}"
            if self._should_skip_request(existing_requests, need_key, force_regenerate):
                continue
            created_item = PersonRequest(
                client_id=client_id,
                person_id=person_id,
                request_type="upload_document",
                title=f"Sube tu {doc_type.upper()}",
                description=f"Documento obligatorio pendiente: {doc_type.upper()}.",
                status="pending",
                resolution_type="document_upload",
                created_by=actor_user_id,
                resolution_payload={"auto_need_key": need_key, "document_type": doc_type},
            )
            self.session.add(created_item)
            existing_requests.insert(0, created_item)
            created.append(created_item)

        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=actor_user_id,
            action="person_requests_generated",
            entity_type="person",
            entity_id=person_id,
            metadata={"created": len(created)},
        )
        return created

    def auto_resolve_requests(self, client_id: str, person_id: str, actor_user_id: str | None = None) -> int:
        completeness = self.get_person_completeness(person_id, client_id)
        missing_fields = set(completeness["missing_fields"])
        missing_documents = set(completeness["missing_documents"])

        active_requests = (
            self.session.query(PersonRequest)
            .filter(
                PersonRequest.client_id == client_id,
                PersonRequest.person_id == person_id,
                PersonRequest.status.in_(tuple(ACTIVE_REQUEST_STATUSES)),
            )
            .all()
        )

        resolved_count = 0
        now = datetime.now(timezone.utc)
        for item in active_requests:
            need_key = self._request_need_key(item)
            if not need_key:
                continue
            if need_key.startswith("field:") and need_key.split(":", 1)[1] in missing_fields:
                continue
            if need_key.startswith("document:") and need_key.split(":", 1)[1] in missing_documents:
                continue

            item.status = "resolved"
            item.review_notes = "Resuelta automáticamente tras completar onboarding."
            item.rejection_reason = None
            item.reviewed_at = now
            item.resolved_at = now
            item.resolved_by = actor_user_id
            resolved_count += 1

        return resolved_count

    def _get_person(self, person_id: str, client_id: str) -> Person:
        return (
            self.session.query(Person)
            .filter(Person.id == person_id, Person.client_id == client_id)
            .one()
        )

    def _evaluate_field_checks(self, person: Person) -> tuple[dict[str, bool], list[str]]:
        missing_fields: list[str] = []
        checks: dict[str, bool] = {}
        for group, fields in self.REQUIRED_FIELDS.items():
            group_ok = True
            for field in fields:
                value = getattr(person, field)
                if value is None or (isinstance(value, str) and not value.strip()):
                    missing_fields.append(field)
                    group_ok = False
            checks[group] = group_ok
        return checks, missing_fields

    def _has_portal_access(self, person_id: str, client_id: str) -> bool:
        user = (
            self.session.query(User)
            .filter(
                User.client_id == client_id,
                User.person_id == person_id,
                User.user_type == "portal",
                User.status.in_(("active", "invited")),
            )
            .order_by(User.created_at.desc())
            .first()
        )
        return user is not None

    @staticmethod
    def _request_need_key(item: PersonRequest) -> str | None:
        payload = item.resolution_payload if isinstance(item.resolution_payload, dict) else {}
        return payload.get("auto_need_key")

    def _should_skip_request(self, existing_requests: list[PersonRequest], need_key: str, force_regenerate: bool) -> bool:
        has_active = any(
            self._request_need_key(item) == need_key and item.status in ACTIVE_REQUEST_STATUSES
            for item in existing_requests
        )
        if has_active:
            return True
        if force_regenerate:
            return False
        has_resolved = any(
            self._request_need_key(item) == need_key and item.status == "resolved"
            for item in existing_requests
        )
        return has_resolved

    @staticmethod
    def _field_request_title(field: str) -> str:
        labels = {
            "email": "Completa tu email",
            "phone": "Completa tu teléfono",
            "address_line1": "Completa tu dirección",
            "city": "Completa tu ciudad",
            "postal_code": "Completa tu código postal",
            "country": "Completa tu país",
            "document_type": "Completa tu tipo de documento",
            "document_number": "Completa tu número de documento",
            "first_name": "Completa tu nombre",
            "last_name": "Completa tu apellido",
        }
        return labels.get(field, f"Completa el campo {field}")
