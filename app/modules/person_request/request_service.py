"""Service layer for person requests."""

from __future__ import annotations

from datetime import datetime, timezone

from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from app.extensions import db
from app.models.case import Case
from app.models.company import Company
from app.models.employee import Employee
from app.models.person import Person
from app.models.person_request import PersonRequest
from app.modules.audit.audit_service import AuditService
from app.modules.documents.service import DocumentModuleService
from app.modules.person_request.request_repository import PersonRequestRepository
from app.modules.person_request.request_schemas import (
    REQUEST_STATUSES,
    PersonRequestCreateRequest,
    PersonRequestSubmitRequest,
    PersonRequestUpdateRequest,
)


class PersonRequestService:
    def __init__(
        self,
        repository: PersonRequestRepository | None = None,
        audit_service: AuditService | None = None,
        document_service: DocumentModuleService | None = None,
    ) -> None:
        self.repository = repository or PersonRequestRepository()
        self.audit_service = audit_service or AuditService()
        self.document_service = document_service or DocumentModuleService()

    def create_person_request(
        self,
        client_id: str,
        person_id: str,
        actor_user_id: str | None,
        payload: PersonRequestCreateRequest,
    ) -> PersonRequest:
        self._ensure_person(client_id, person_id)
        self._validate_related_entities(client_id, payload.company_id, payload.case_id, payload.employee_id)

        item = PersonRequest(
            client_id=client_id,
            person_id=person_id,
            company_id=payload.company_id,
            case_id=payload.case_id,
            employee_id=payload.employee_id,
            request_type=payload.request_type,
            title=payload.title,
            description=payload.description,
            due_date=payload.due_date,
            resolution_type=payload.resolution_type,
            status="pending",
            created_by=actor_user_id,
        )
        self.repository.add(item)
        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=actor_user_id,
            action="person_request_created",
            entity_type="person_request",
            entity_id=item.id,
            metadata={"person_id": person_id, "request_type": payload.request_type},
        )
        return item

    def list_person_requests(
        self,
        client_id: str,
        person_id: str,
        status: str | None = None,
        request_type: str | None = None,
    ) -> list[PersonRequest]:
        self._ensure_person(client_id, person_id)
        if status and status not in REQUEST_STATUSES:
            raise BadRequest("invalid_status")
        return self.repository.list_person_requests(client_id, person_id, status=status, request_type=request_type)

    def get_person_request(self, client_id: str, request_id: str) -> PersonRequest:
        item = self.repository.get_by_id(client_id, request_id)
        if item is None:
            raise NotFound("person_request_not_found")
        return item

    def update_person_request(
        self,
        client_id: str,
        request_id: str,
        payload: PersonRequestUpdateRequest,
    ) -> PersonRequest:
        item = self.get_person_request(client_id, request_id)
        if payload.title is not None:
            item.title = payload.title
        if payload.description is not None:
            item.description = payload.description
        if payload.due_date is not None:
            item.due_date = payload.due_date
        if payload.status is not None:
            if item.status == "resolved" and payload.status == "cancelled":
                raise BadRequest("cannot_cancel_resolved_request")
            item.status = payload.status
        if payload.resolution_type is not None:
            item.resolution_type = payload.resolution_type
        return item

    def resolve_person_request(
        self,
        client_id: str,
        request_id: str,
        actor_user_id: str | None,
        resolution_payload: dict | None = None,
        status: str = "resolved",
        audit_action: str = "person_request_resolved",
    ) -> PersonRequest:
        item = self.get_person_request(client_id, request_id)
        if item.status == "cancelled":
            raise BadRequest("cannot_resolve_cancelled_request")
        item.status = status
        item.resolution_payload = resolution_payload or {}
        item.resolved_by = actor_user_id
        item.resolved_at = datetime.now(timezone.utc)
        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=actor_user_id,
            action=audit_action,
            entity_type="person_request",
            entity_id=item.id,
            metadata={"status": item.status},
        )
        return item

    def cancel_person_request(self, client_id: str, request_id: str, actor_user_id: str | None) -> PersonRequest:
        item = self.get_person_request(client_id, request_id)
        if item.status == "resolved":
            raise BadRequest("cannot_cancel_resolved_request")
        item.status = "cancelled"
        self.audit_service.log_action(
            client_id=client_id,
            actor_user_id=actor_user_id,
            action="person_request_cancelled",
            entity_type="person_request",
            entity_id=item.id,
        )
        return item


    def portal_dashboard_summary(self, user, client_id: str) -> dict:
        person_id = self._require_portal_person(user)
        items = self.repository.list_person_requests(client_id, person_id)
        now = datetime.now(timezone.utc).date()
        pending = [item for item in items if item.status in {"pending", "in_progress"}]
        overdue = [item for item in pending if item.due_date and item.due_date < now]
        resolved_recent = [item for item in items if item.status == "resolved"][:5]
        return {
            "pending_requests": len(pending),
            "overdue_requests": len(overdue),
            "recently_resolved_requests": len(resolved_recent),
        }

    def portal_list_requests(self, user, client_id: str, status: str | None = None) -> list[PersonRequest]:
        person_id = self._require_portal_person(user)
        return self.list_person_requests(client_id, person_id, status=status)

    def portal_get_request(self, user, client_id: str, request_id: str) -> PersonRequest:
        person_id = self._require_portal_person(user)
        item = self.get_person_request(client_id, request_id)
        if item.person_id != person_id:
            raise Forbidden("portal_request_forbidden")
        return item

    def portal_submit_request(
        self,
        user,
        client_id: str,
        request_id: str,
        payload: PersonRequestSubmitRequest,
    ) -> PersonRequest:
        item = self.portal_get_request(user, client_id, request_id)
        target_status = "resolved" if item.resolution_type in {"form_submission", "confirm_information", "auto_resolved"} else "in_progress"
        return self.resolve_person_request(
            client_id=client_id,
            request_id=request_id,
            actor_user_id=str(user.id),
            resolution_payload=payload.payload,
            status=target_status,
            audit_action="portal_request_submitted",
        )

    def portal_upload_request(self, user, client_id: str, request_id: str, file: FileStorage) -> PersonRequest:
        item = self.portal_get_request(user, client_id, request_id)
        if item.resolution_type != "document_upload":
            raise BadRequest("invalid_resolution_type")

        document = self.document_service.upload_document(
            client_id=client_id,
            actor_user_id=str(user.id),
            file=file,
            company_id=item.company_id,
            case_id=item.case_id,
            person_id=item.person_id,
            employee_id=item.employee_id,
            doc_type="person_request_upload",
            status="pending",
        )
        db.session.flush()
        return self.resolve_person_request(
            client_id=client_id,
            request_id=request_id,
            actor_user_id=str(user.id),
            resolution_payload={"document_id": document.id, "file_name": document.original_filename},
            status="resolved",
            audit_action="portal_request_file_uploaded",
        )

    @staticmethod
    def _require_portal_person(user) -> str:
        person_id = getattr(user, "person_id", None)
        if not person_id:
            raise Forbidden("portal_user_requires_person")
        return str(person_id)

    @staticmethod
    def _ensure_person(client_id: str, person_id: str) -> None:
        person = (
            db.session.query(Person)
            .filter(Person.client_id == client_id, Person.id == person_id)
            .one_or_none()
        )
        if person is None:
            raise NotFound("person_not_found")

    @staticmethod
    def _validate_related_entities(
        client_id: str,
        company_id: str | None,
        case_id: str | None,
        employee_id: str | None,
    ) -> None:
        if company_id:
            company = (
                db.session.query(Company)
                .filter(Company.client_id == client_id, Company.id == company_id)
                .one_or_none()
            )
            if company is None:
                raise BadRequest("invalid_company_id")
        if case_id:
            case = db.session.query(Case).filter(Case.client_id == client_id, Case.id == case_id).one_or_none()
            if case is None:
                raise BadRequest("invalid_case_id")
            if company_id and case.company_id != company_id:
                raise BadRequest("case_company_mismatch")
        if employee_id:
            employee = (
                db.session.query(Employee)
                .filter(Employee.client_id == client_id, Employee.id == employee_id)
                .one_or_none()
            )
            if employee is None:
                raise BadRequest("invalid_employee_id")
            if company_id and employee.company_id != company_id:
                raise BadRequest("employee_company_mismatch")
