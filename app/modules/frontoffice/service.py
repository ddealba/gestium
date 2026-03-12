"""Frontoffice service layer."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from werkzeug.exceptions import Forbidden, NotFound

from app.extensions import db
from app.models.company import Company
from app.models.person_request import PersonRequest
from app.models.person import Person
from app.models.person_company_relation import PersonCompanyRelation
from app.modules.frontoffice.schemas import (
    serialize_case,
    serialize_company_relation,
    serialize_document,
    serialize_profile,
)
from app.modules.notification.notification_service import NotificationService, serialize_notification
from app.modules.portal.visibility_service import PortalVisibilityService


class FrontofficeService:
    """Provides person-scoped frontoffice reads."""

    def __init__(self) -> None:
        self.visibility = PortalVisibilityService()
        self.notification_service = NotificationService()

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

    def get_portal_home(self, user, client_id: str) -> dict:
        person_id = self._ensure_person_id(user)
        now = datetime.now(timezone.utc)
        today = now.date()
        recent_cutoff = now - timedelta(days=7)

        documents = self.visibility.get_portal_documents(person_id, client_id)
        cases = self.visibility.get_portal_cases(person_id, client_id)
        companies = self.get_portal_companies(user, client_id)
        employee_ids = self.visibility.get_portal_visible_employee_ids(person_id, client_id)

        requests = (
            db.session.query(PersonRequest)
            .filter(PersonRequest.client_id == client_id, PersonRequest.person_id == person_id)
            .order_by(PersonRequest.created_at.desc())
            .all()
        )

        actionable_statuses = {"pending", "submitted", "in_review", "rejected", "expired"}
        pending_requests = [item for item in requests if item.status in actionable_statuses]
        overdue_requests = [
            item
            for item in pending_requests
            if item.due_date is not None and item.due_date < today
        ]
        recent_documents = [
            item
            for item in documents
            if item.created_at and self._as_utc(item.created_at) >= recent_cutoff
        ]
        open_cases = [
            item
            for item in cases
            if item.status not in {"closed", "resolved", "cancelled"}
        ]

        tasks = self._build_portal_tasks(pending_requests, today)
        activity = self._build_portal_activity(documents, cases, requests)

        notifications = self.notification_service.list_notifications_for_portal(
            client_id=client_id,
            person_id=person_id,
        )

        return {
            "summary": {
                "pending_requests": len(pending_requests),
                "overdue_requests": len(overdue_requests),
                "recent_documents": len(recent_documents),
                "open_cases": len(open_cases),
                "companies_count": len(companies),
            },
            "tasks": tasks,
            "activity": activity,
            "contexts": {
                "has_personal_area": True,
                "has_employee_area": len(employee_ids) > 0,
                "has_company_area": len(companies) > 0,
            },
            "companies": companies,
            "notifications": {
                "unread_count": len([item for item in notifications if item.status == "unread"]),
                "items": [serialize_notification(item) for item in notifications[:5]],
            },
        }

    @staticmethod
    def _build_portal_tasks(requests: list[PersonRequest], today) -> list[dict]:
        prioritized: list[PersonRequest] = []
        seen: set[str] = set()

        def append_unique(items: list[PersonRequest]) -> None:
            for item in items:
                if item.id in seen:
                    continue
                seen.add(item.id)
                prioritized.append(item)

        overdue = [item for item in requests if item.due_date and item.due_date < today]
        near_due = sorted(
            [item for item in requests if item.due_date and item.due_date >= today],
            key=lambda item: item.due_date,
        )
        upload = [item for item in requests if item.resolution_type == "document_upload"]
        confirm = [item for item in requests if item.resolution_type == "confirm_information"]

        append_unique(overdue)
        append_unique(near_due)
        append_unique(upload)
        append_unique(confirm)
        append_unique(sorted([item for item in requests if item.id not in seen], key=lambda item: (item.created_at or datetime.min).isoformat(), reverse=True))

        items = []
        for item in prioritized[:8]:
            cta_label = "Resolver ahora"
            if item.resolution_type == "document_upload":
                cta_label = "Subir documento"
            elif item.resolution_type in {"confirm_information", "manual_review"}:
                cta_label = "Ver detalle"

            if item.due_date and item.due_date < today:
                priority = "overdue"
            elif item.resolution_type == "document_upload":
                priority = "upload"
            elif item.resolution_type == "confirm_information":
                priority = "confirmation"
            else:
                priority = "pending"

            items.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "status": item.status,
                    "due_date": item.due_date.isoformat() if item.due_date else None,
                    "resolution_type": item.resolution_type,
                    "priority": priority,
                    "cta_label": cta_label,
                    "cta_url": f"/portal/requests/{item.id}",
                }
            )
        return items


    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _build_portal_activity(documents, cases, requests: list[PersonRequest]) -> list[dict]:
        activity = []

        for item in documents[:4]:
            activity.append(
                {
                    "type": "document",
                    "message": f"Nuevo documento disponible: {item.original_filename}",
                    "date": item.created_at.isoformat() if item.created_at else None,
                    "url": "/portal/documents",
                }
            )

        for item in cases[:4]:
            updated_at = item.updated_at or item.created_at
            activity.append(
                {
                    "type": "case",
                    "message": f"Expediente actualizado: {item.title}",
                    "date": updated_at.isoformat() if updated_at else None,
                    "url": "/portal/cases",
                }
            )

        for item in requests[:4]:
            event = "resuelta" if item.status == "resolved" else ("rechazada" if item.status == "rejected" else "actualizada")
            stamp = item.resolved_at if item.status == "resolved" else (item.reviewed_at or item.submitted_at or item.created_at)
            activity.append(
                {
                    "type": "request",
                    "message": f"Solicitud {event}: {item.title}",
                    "date": stamp.isoformat() if stamp else None,
                    "url": f"/portal/requests/{item.id}",
                }
            )

        return sorted(activity, key=lambda item: item["date"] or "", reverse=True)[:10]
