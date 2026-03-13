"""Repository layer for dashboard summary queries."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from sqlalchemy import and_, case, distinct, func, not_, or_

from app.extensions import db
from app.models.case import Case
from app.models.case_event import CaseEvent
from app.models.company import Company
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.models.employee import Employee
from app.models.person import Person
from app.models.person_company_relation import PersonCompanyRelation
from app.models.person_request import PersonRequest
from app.models.user import User

ACTIVE_CASE_STATUSES = ("open", "in_progress", "waiting")
TERMINAL_CASE_STATUSES = ("done", "cancelled")
CASE_STATUS_ORDER = ["open", "in_progress", "waiting", "done", "cancelled"]
DOC_STATUS_ORDER = ["pending", "processed", "archived"]
OPEN_REQUEST_STATUSES = ("pending", "submitted", "in_review", "rejected")


class DashboardRepository:
    """Data access for tenant dashboard aggregates."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def count_active_cases(self, client_id: str) -> int:
        return (
            self.session.query(func.count(Case.id))
            .filter(Case.client_id == client_id, Case.status.in_(ACTIVE_CASE_STATUSES))
            .scalar()
            or 0
        )

    def count_overdue_cases(self, client_id: str, today: date) -> int:
        return (
            self.session.query(func.count(Case.id))
            .filter(
                Case.client_id == client_id,
                Case.due_date.isnot(None),
                Case.due_date < today,
                not_(Case.status.in_(TERMINAL_CASE_STATUSES)),
            )
            .scalar()
            or 0
        )

    def count_due_today(self, client_id: str, today: date) -> int:
        return (
            self.session.query(func.count(Case.id))
            .filter(
                Case.client_id == client_id,
                Case.due_date == today,
                not_(Case.status.in_(TERMINAL_CASE_STATUSES)),
            )
            .scalar()
            or 0
        )

    def count_docs_pending(self, client_id: str) -> int:
        return (
            self.session.query(func.count(Document.id))
            .filter(Document.client_id == client_id, Document.status == "pending")
            .scalar()
            or 0
        )

    def count_my_active_cases(self, client_id: str, user_id: str) -> int:
        return (
            self.session.query(func.count(Case.id))
            .filter(
                Case.client_id == client_id,
                Case.responsible_user_id == user_id,
                Case.status.in_(ACTIVE_CASE_STATUSES),
            )
            .scalar()
            or 0
        )

    def count_active_companies(self, client_id: str) -> int:
        return (
            self.session.query(func.count(Company.id))
            .filter(Company.client_id == client_id, Company.status == "active")
            .scalar()
            or 0
        )

    def count_companies_with_open_cases(self, client_id: str) -> int:
        return (
            self.session.query(func.count(distinct(Case.company_id)))
            .join(Company, Company.id == Case.company_id)
            .filter(
                Company.client_id == client_id,
                Case.client_id == client_id,
                Case.status.in_(ACTIVE_CASE_STATUSES),
            )
            .scalar()
            or 0
        )

    def count_total_active_employees(self, client_id: str) -> int:
        return (
            self.session.query(func.count(Employee.id))
            .join(Company, Company.id == Employee.company_id)
            .filter(Company.client_id == client_id, Employee.status == "active")
            .scalar()
            or 0
        )

    def count_total_docs(self, client_id: str) -> int:
        return (
            self.session.query(func.count(Document.id))
            .filter(Document.client_id == client_id)
            .scalar()
            or 0
        )

    def count_docs_with_extraction(self, client_id: str) -> int:
        return (
            self.session.query(func.count(distinct(DocumentExtraction.document_id)))
            .filter(DocumentExtraction.client_id == client_id)
            .scalar()
            or 0
        )

    def count_cases_created_since(self, client_id: str, start_ts: datetime) -> int:
        return (
            self.session.query(func.count(Case.id))
            .filter(Case.client_id == client_id, Case.created_at >= start_ts)
            .scalar()
            or 0
        )

    def count_docs_uploaded_since(self, client_id: str, start_ts: datetime) -> int:
        return (
            self.session.query(func.count(Document.id))
            .filter(Document.client_id == client_id, Document.created_at >= start_ts)
            .scalar()
            or 0
        )

    def cases_by_status(self, client_id: str) -> dict[str, int]:
        rows = (
            self.session.query(Case.status, func.count(Case.id))
            .filter(Case.client_id == client_id)
            .group_by(Case.status)
            .all()
        )
        return {status: count for status, count in rows}

    def docs_by_status(self, client_id: str) -> dict[str, int]:
        rows = (
            self.session.query(Document.status, func.count(Document.id))
            .filter(Document.client_id == client_id)
            .group_by(Document.status)
            .all()
        )
        return {status: count for status, count in rows}

    def overdue_cases(self, client_id: str, today: date, limit: int) -> list[dict]:
        rows = (
            self.session.query(
                Case.id,
                Case.title,
                Case.type,
                Case.status,
                Case.due_date,
                Company.id,
                Company.name,
                Case.responsible_user_id,
                User.email,
            )
            .join(Company, Company.id == Case.company_id)
            .outerjoin(User, User.id == Case.responsible_user_id)
            .filter(
                Case.client_id == client_id,
                Case.due_date.isnot(None),
                Case.due_date < today,
                not_(Case.status.in_(TERMINAL_CASE_STATUSES)),
            )
            .order_by(Case.due_date.asc(), Case.created_at.asc())
            .limit(max(limit, 1))
            .all()
        )

        return [
            {
                "case_id": case_id,
                "title": title,
                "case_type": case_type,
                "status": status,
                "due_date": due_date.isoformat() if due_date else None,
                "company_id": company_id,
                "company_name": company_name,
                "responsible_user_id": responsible_user_id,
                "responsible_email": responsible_email,
            }
            for (
                case_id,
                title,
                case_type,
                status,
                due_date,
                company_id,
                company_name,
                responsible_user_id,
                responsible_email,
            ) in rows
        ]

    def my_cases(self, client_id: str, user_id: str, limit: int) -> list[dict]:
        rows = (
            self.session.query(Case.id, Case.title, Case.company_id, Company.name, Case.status, Case.due_date)
            .join(Company, Company.id == Case.company_id)
            .filter(
                Case.client_id == client_id,
                Case.responsible_user_id == user_id,
                Case.status.in_(ACTIVE_CASE_STATUSES),
            )
            .order_by(Case.due_date.asc().nullslast(), Case.created_at.asc())
            .limit(max(limit, 1))
            .all()
        )

        return [
            {
                "case_id": case_id,
                "title": title,
                "company_id": company_id,
                "company_name": company_name,
                "status": status,
                "due_date": due_date.isoformat() if due_date else None,
            }
            for case_id, title, company_id, company_name, status, due_date in rows
        ]

    def employees_by_company(self, client_id: str, limit: int = 6) -> dict[str, list]:
        rows = (
            self.session.query(Company.name, func.count(Employee.id))
            .join(Employee, Employee.company_id == Company.id)
            .filter(Company.client_id == client_id)
            .group_by(Company.name)
            .order_by(func.count(Employee.id).desc(), Company.name.asc())
            .limit(max(limit, 1))
            .all()
        )
        return {
            "labels": [name for name, _ in rows],
            "values": [int(total) for _, total in rows],
        }

    def case_events_for_activity(self, client_id: str, limit: int) -> list[dict]:
        rows = (
            self.session.query(
                CaseEvent.created_at,
                CaseEvent.event_type,
                CaseEvent.payload,
                CaseEvent.case_id,
                CaseEvent.company_id,
                Company.name,
                Case.title,
            )
            .join(Case, and_(Case.id == CaseEvent.case_id, Case.client_id == client_id))
            .join(Company, and_(Company.id == CaseEvent.company_id, Company.client_id == client_id))
            .filter(CaseEvent.client_id == client_id)
            .order_by(CaseEvent.created_at.desc())
            .limit(max(limit, 1) * 3)
            .all()
        )

        items: list[dict] = []
        for ts, event_type, payload, case_id, company_id, company_name, case_title in rows:
            payload = payload or {}
            kind = "case_status_changed"
            title = f"Expediente actualizado: {case_title}"
            if event_type == "status_change":
                if payload.get("from") is None and payload.get("to") == "open":
                    kind = "case_created"
                    title = f"Expediente creado: {case_title}"
                else:
                    to_status = payload.get("to") or "actualizado"
                    kind = "case_status_changed"
                    title = f"Estado cambiado a {to_status}: {case_title}"
            elif event_type == "attachment":
                kind = "document_uploaded"
                title = payload.get("filename") or f"Documento adjunto en: {case_title}"
            elif event_type == "comment":
                kind = "case_status_changed"
                title = f"Nuevo comentario en: {case_title}"

            items.append(
                {
                    "ts": ts.isoformat() if ts else None,
                    "kind": kind,
                    "title": title,
                    "company_id": company_id,
                    "company_name": company_name,
                    "case_id": case_id,
                    "document_id": payload.get("document_id"),
                    "_sort_ts": ts,
                }
            )
        return items

    def documents_for_activity(self, client_id: str, limit: int) -> list[dict]:
        rows = (
            self.session.query(Document.created_at, Document.id, Document.case_id, Document.company_id, Company.name)
            .join(Company, and_(Company.id == Document.company_id, Company.client_id == client_id))
            .filter(Document.client_id == client_id)
            .order_by(Document.created_at.desc())
            .limit(max(limit, 1))
            .all()
        )
        return [
            {
                "ts": ts.isoformat() if ts else None,
                "kind": "document_uploaded",
                "title": "Documento subido",
                "company_id": company_id,
                "company_name": company_name,
                "case_id": case_id,
                "document_id": document_id,
                "_sort_ts": ts,
            }
            for ts, document_id, case_id, company_id, company_name in rows
        ]

    def extractions_for_activity(self, client_id: str, limit: int) -> list[dict]:
        rows = (
            self.session.query(
                DocumentExtraction.created_at,
                DocumentExtraction.document_id,
                DocumentExtraction.case_id,
                DocumentExtraction.company_id,
                Company.name,
            )
            .join(Company, and_(Company.id == DocumentExtraction.company_id, Company.client_id == client_id))
            .filter(DocumentExtraction.client_id == client_id)
            .order_by(DocumentExtraction.created_at.desc())
            .limit(max(limit, 1))
            .all()
        )

        return [
            {
                "ts": ts.isoformat() if ts else None,
                "kind": "extraction_created",
                "title": "Extracción generada",
                "company_id": company_id,
                "company_name": company_name,
                "case_id": case_id,
                "document_id": document_id,
                "_sort_ts": ts,
            }
            for ts, document_id, case_id, company_id, company_name in rows
        ]

    def count_persons(self, client_id: str) -> int:
        return self.session.query(func.count(Person.id)).filter(Person.client_id == client_id).scalar() or 0

    def count_persons_active(self, client_id: str) -> int:
        return (
            self.session.query(func.count(Person.id))
            .filter(Person.client_id == client_id, Person.status == "active")
            .scalar()
            or 0
        )

    def count_persons_incomplete(self, client_id: str) -> int:
        return (
            self.session.query(func.count(Person.id))
            .filter(Person.client_id == client_id, Person.status.in_(("draft", "pending_info")))
            .scalar()
            or 0
        )

    def count_pending_requests(self, client_id: str) -> int:
        return (
            self.session.query(func.count(PersonRequest.id))
            .filter(PersonRequest.client_id == client_id, PersonRequest.status.in_(OPEN_REQUEST_STATUSES))
            .scalar()
            or 0
        )

    def count_overdue_requests(self, client_id: str, today: date) -> int:
        return (
            self.session.query(func.count(PersonRequest.id))
            .filter(
                PersonRequest.client_id == client_id,
                PersonRequest.status.in_(OPEN_REQUEST_STATUSES),
                PersonRequest.due_date.isnot(None),
                PersonRequest.due_date < today,
            )
            .scalar()
            or 0
        )

    def count_requests_submitted_today(self, client_id: str, today: date) -> int:
        return (
            self.session.query(func.count(PersonRequest.id))
            .filter(
                PersonRequest.client_id == client_id,
                PersonRequest.submitted_at.isnot(None),
                func.date(PersonRequest.submitted_at) == today,
            )
            .scalar()
            or 0
        )

    def count_documents_today(self, client_id: str, today: date) -> int:
        return (
            self.session.query(func.count(Document.id))
            .filter(Document.client_id == client_id, func.date(Document.created_at) == today)
            .scalar()
            or 0
        )

    def count_cases_open(self, client_id: str) -> int:
        return (
            self.session.query(func.count(Case.id))
            .filter(Case.client_id == client_id, not_(Case.status.in_(TERMINAL_CASE_STATUSES)))
            .scalar()
            or 0
        )

    def attention_persons(self, client_id: str, today: date, limit: int = 20) -> list[dict]:
        request_counts = (
            self.session.query(
                PersonRequest.person_id.label("person_id"),
                func.count(PersonRequest.id).label("pending_requests"),
                func.sum(case((PersonRequest.due_date < today, 1), else_=0)).label("overdue_requests"),
            )
            .filter(
                PersonRequest.client_id == client_id,
                PersonRequest.status.in_(OPEN_REQUEST_STATUSES),
            )
            .group_by(PersonRequest.person_id)
            .subquery()
        )

        rows = (
            self.session.query(
                Person.id,
                Person.first_name,
                Person.last_name,
                Person.status,
                Person.updated_at,
                func.min(Company.id),
                func.min(Company.name),
                func.coalesce(request_counts.c.pending_requests, 0),
                func.coalesce(request_counts.c.overdue_requests, 0),
            )
            .outerjoin(
                PersonCompanyRelation,
                and_(
                    PersonCompanyRelation.person_id == Person.id,
                    PersonCompanyRelation.client_id == client_id,
                    PersonCompanyRelation.status == "active",
                ),
            )
            .outerjoin(Company, and_(Company.id == PersonCompanyRelation.company_id, Company.client_id == client_id))
            .outerjoin(request_counts, request_counts.c.person_id == Person.id)
            .filter(
                Person.client_id == client_id,
                or_(
                    Person.status.in_(("draft", "pending_info")),
                    func.coalesce(request_counts.c.overdue_requests, 0) > 0,
                    func.coalesce(request_counts.c.pending_requests, 0) > 0,
                ),
            )
            .group_by(
                Person.id,
                Person.first_name,
                Person.last_name,
                Person.status,
                Person.updated_at,
                request_counts.c.pending_requests,
                request_counts.c.overdue_requests,
            )
            .order_by(
                case((Person.status.in_(("draft", "pending_info")), 0), else_=1),
                case((func.coalesce(request_counts.c.overdue_requests, 0) > 0, 0), else_=1),
                func.coalesce(request_counts.c.pending_requests, 0).desc(),
                Person.updated_at.asc(),
            )
            .limit(max(limit, 1))
            .all()
        )

        return [
            {
                "person_id": person_id,
                "person_name": f"{first_name} {last_name}".strip(),
                "company_id": company_id,
                "company_name": company_name,
                "onboarding_status": status,
                "pending_requests": int(pending_requests or 0),
                "overdue_requests": int(overdue_requests or 0),
                "last_activity": updated_at.isoformat() if updated_at else None,
            }
            for (
                person_id,
                first_name,
                last_name,
                status,
                updated_at,
                company_id,
                company_name,
                pending_requests,
                overdue_requests,
            ) in rows
        ]

    def pending_requests(self, client_id: str, today: date, limit: int = 30) -> list[dict]:
        rows = (
            self.session.query(
                PersonRequest.id,
                PersonRequest.person_id,
                Person.first_name,
                Person.last_name,
                PersonRequest.company_id,
                Company.name,
                PersonRequest.request_type,
                PersonRequest.status,
                PersonRequest.due_date,
            )
            .join(Person, and_(Person.id == PersonRequest.person_id, Person.client_id == client_id))
            .outerjoin(Company, and_(Company.id == PersonRequest.company_id, Company.client_id == client_id))
            .filter(PersonRequest.client_id == client_id, PersonRequest.status.in_(OPEN_REQUEST_STATUSES))
            .order_by(
                case((PersonRequest.due_date < today, 0), else_=1),
                case((and_(PersonRequest.due_date.isnot(None), PersonRequest.due_date >= today, PersonRequest.due_date <= today + timedelta(days=3)), 0), else_=1),
                PersonRequest.due_date.asc().nullslast(),
                PersonRequest.created_at.asc(),
            )
            .limit(max(limit, 1))
            .all()
        )

        return [
            {
                "request_id": request_id,
                "person_id": person_id,
                "person_name": f"{first_name} {last_name}".strip(),
                "company_id": company_id,
                "company_name": company_name,
                "request_type": request_type,
                "status": status,
                "due_date": due_date.isoformat() if due_date else None,
            }
            for request_id, person_id, first_name, last_name, company_id, company_name, request_type, status, due_date in rows
        ]

    def recent_documents(self, client_id: str, limit: int = 20) -> list[dict]:
        rows = (
            self.session.query(
                Document.id,
                Document.person_id,
                Person.first_name,
                Person.last_name,
                Document.company_id,
                Company.name,
                Document.doc_type,
                Document.created_at,
                Document.status,
            )
            .outerjoin(Person, and_(Person.id == Document.person_id, Person.client_id == client_id))
            .outerjoin(Company, and_(Company.id == Document.company_id, Company.client_id == client_id))
            .filter(Document.client_id == client_id)
            .order_by(Document.created_at.desc())
            .limit(max(limit, 1))
            .all()
        )
        return [
            {
                "document_id": document_id,
                "person_id": person_id,
                "person_name": (f"{first_name} {last_name}".strip() if first_name else None),
                "company_id": company_id,
                "company_name": company_name,
                "document_type": doc_type,
                "uploaded_at": created_at.isoformat() if created_at else None,
                "status": status,
            }
            for document_id, person_id, first_name, last_name, company_id, company_name, doc_type, created_at, status in rows
        ]

    def cases_needing_attention(self, client_id: str, today: date, limit: int = 20) -> list[dict]:
        rows = (
            self.session.query(
                Case.id,
                Case.company_id,
                Company.name,
                Case.person_id,
                Person.first_name,
                Person.last_name,
                Case.title,
                Case.status,
                Case.due_date,
            )
            .outerjoin(Company, and_(Company.id == Case.company_id, Company.client_id == client_id))
            .outerjoin(Person, and_(Person.id == Case.person_id, Person.client_id == client_id))
            .filter(
                Case.client_id == client_id,
                not_(Case.status.in_(TERMINAL_CASE_STATUSES)),
                Case.due_date.isnot(None),
                Case.due_date < today,
            )
            .order_by(Case.due_date.asc(), Case.created_at.asc())
            .limit(max(limit, 1))
            .all()
        )
        return [
            {
                "case_id": case_id,
                "company_id": company_id,
                "company_name": company_name,
                "person_id": person_id,
                "person_name": (f"{first_name} {last_name}".strip() if first_name else None),
                "title": title,
                "status": status,
                "due_date": due_date.isoformat() if due_date else None,
            }
            for case_id, company_id, company_name, person_id, first_name, last_name, title, status, due_date in rows
        ]
