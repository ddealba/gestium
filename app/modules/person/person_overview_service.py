"""Aggregated person overview service for backoffice 360 view."""

from __future__ import annotations


from app.extensions import db
from app.models.case import Case
from app.models.company import Company
from app.models.document import Document
from app.models.employee import Employee
from app.models.person_request import PersonRequest
from app.models.user import User
from app.modules.audit.models import AuditLog
from app.modules.person.person_repository import PersonRepository
from app.modules.person.person_schemas import PersonResponseSchema
from app.modules.person_company_relation.relation_repository import PersonCompanyRelationRepository


class PersonOverviewService:
    """Compose a person-centric 360 overview payload."""

    def __init__(
        self,
        person_repository: PersonRepository | None = None,
        relation_repository: PersonCompanyRelationRepository | None = None,
    ) -> None:
        self.person_repository = person_repository or PersonRepository()
        self.relation_repository = relation_repository or PersonCompanyRelationRepository()
        self.session = db.session

    def build_overview(self, client_id: str, person_id: str) -> dict:
        person = self.person_repository.get_person_by_id(person_id, client_id)
        if person is None:
            from werkzeug.exceptions import NotFound

            raise NotFound("Person not found.")

        person_payload = PersonResponseSchema.dump(person)
        portal_user = self._get_portal_user(client_id, person.id)
        relations = self.relation_repository.list_relations_by_person(person.id, client_id)
        employee = self._get_employee(client_id, person.id)
        cases = self._list_cases(client_id, person.id)
        documents = self._list_documents(client_id, person.id)
        requests = self._list_requests(client_id, person.id)

        return {
            "person": person_payload,
            "completeness": self._build_completeness(person_payload, portal_user),
            "companies": [
                {
                    "relation_id": relation.id,
                    "company_id": company.id,
                    "company_name": company.name,
                    "relation_type": relation.relation_type,
                    "status": relation.status,
                    "start_date": relation.start_date.isoformat() if relation.start_date else None,
                    "end_date": relation.end_date.isoformat() if relation.end_date else None,
                }
                for relation, company in relations
            ],
            "employee": employee,
            "cases": cases,
            "documents": documents,
            "requests": requests,
            "portal_access": self._build_portal_access(portal_user),
            "audit": self._list_audit(client_id, person.id),
        }

    def _build_completeness(self, person_payload: dict, portal_user: User | None) -> dict:
        basic_complete = all(
            [
                bool(person_payload.get("first_name")),
                bool(person_payload.get("last_name")),
                bool(person_payload.get("document_number")),
                bool(person_payload.get("address_line1")),
                bool(person_payload.get("city")),
                bool(person_payload.get("country")),
                bool(person_payload.get("status")),
            ]
        )
        flags = {
            "basic_data_complete": basic_complete,
            "identification_document_present": bool(person_payload.get("document_number")),
            "email_present": bool(person_payload.get("email")),
            "phone_present": bool(person_payload.get("phone")),
            "portal_access_created": portal_user is not None,
        }
        score = sum(1 for value in flags.values() if value)
        percentage = int(round((score / len(flags)) * 100)) if flags else 0
        return {**flags, "completion_percentage": percentage}

    def _get_portal_user(self, client_id: str, person_id: str) -> User | None:
        return (
            self.session.query(User)
            .filter(
                User.client_id == client_id,
                User.person_id == person_id,
                User.user_type == "portal",
            )
            .order_by(User.created_at.desc())
            .first()
        )

    @staticmethod
    def _build_portal_access(portal_user: User | None) -> dict | None:
        if portal_user is None:
            return None
        return {
            "user_id": portal_user.id,
            "email": portal_user.email,
            "status": portal_user.status,
            "can_regenerate_invitation": portal_user.status == "invited",
        }

    def _get_employee(self, client_id: str, person_id: str) -> dict | None:
        row = (
            self.session.query(Employee, Company)
            .outerjoin(Company, Company.id == Employee.company_id)
            .filter(Employee.client_id == client_id, Employee.person_id == person_id)
            .order_by(Employee.created_at.desc())
            .first()
        )
        if row is None:
            return None
        employee, company = row
        return {
            "id": employee.id,
            "company_id": employee.company_id,
            "company_name": company.name if company else None,
            "employment_status": employee.status,
            "start_date": employee.start_date.isoformat() if employee.start_date else None,
            "end_date": employee.end_date.isoformat() if employee.end_date else None,
            "detail_url": f"/companies/{employee.company_id}/employees/{employee.id}",
        }

    def _list_cases(self, client_id: str, person_id: str) -> list[dict]:
        rows = (
            self.session.query(Case, Company)
            .outerjoin(Company, Company.id == Case.company_id)
            .filter(Case.client_id == client_id, Case.person_id == person_id)
            .order_by(Case.created_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": case.id,
                "title": case.title,
                "type": case.type,
                "company_id": case.company_id,
                "company_name": company.name if company else None,
                "status": case.status,
                "due_date": case.due_date.isoformat() if case.due_date else None,
                "detail_url": f"/app/companies/{case.company_id}/cases/{case.id}" if case.company_id else None,
            }
            for case, company in rows
        ]

    def _list_documents(self, client_id: str, person_id: str) -> list[dict]:
        rows = (
            self.session.query(Document)
            .filter(Document.client_id == client_id, Document.person_id == person_id)
            .order_by(Document.created_at.desc())
            .limit(50)
            .all()
        )
        items = []
        for document in rows:
            contexts: list[str] = []
            contexts.append("personal")
            if document.employee_id:
                contexts.append("laboral")
            if document.company_id:
                contexts.append("empresa")
            if document.case_id:
                contexts.append("expediente")
            items.append(
                {
                    "id": document.id,
                    "name": document.original_filename,
                    "type": document.doc_type,
                    "status": document.status,
                    "contexts": contexts,
                    "download_url": f"/documents/{document.id}/download",
                    "detail_url": f"/documents/{document.id}",
                }
            )
        return items

    def _list_requests(self, client_id: str, person_id: str) -> list[dict]:
        rows = (
            self.session.query(PersonRequest)
            .filter(PersonRequest.client_id == client_id, PersonRequest.person_id == person_id)
            .order_by(PersonRequest.created_at.desc())
            .limit(50)
            .all()
        )
        return [
            {
                "id": item.id,
                "title": item.title,
                "type": item.request_type,
                "status": item.status,
                "due_date": item.due_date.isoformat() if item.due_date else None,
                "resolution_type": item.resolution_type,
            }
            for item in rows
        ]

    def _list_audit(self, client_id: str, person_id: str) -> list[dict]:
        rows = (
            self.session.query(AuditLog)
            .filter(AuditLog.client_id == client_id)
            .order_by(AuditLog.created_at.desc())
            .limit(200)
            .all()
        )
        filtered: list[AuditLog] = []
        for row in rows:
            metadata = row.metadata_json if isinstance(row.metadata_json, dict) else {}
            if (row.entity_type == "person" and row.entity_id == person_id) or metadata.get("person_id") == person_id:
                filtered.append(row)
            if len(filtered) == 10:
                break
        return [
            {
                "id": row.id,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in filtered
        ]
