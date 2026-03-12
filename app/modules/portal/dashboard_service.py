"""Portal dashboard orchestration service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.person_request import PersonRequest
from app.modules.portal.visibility_service import PortalVisibilityService


class PortalDashboardService:
    """Build portal home summary, tasks and activity payloads."""

    def __init__(self, visibility_service: PortalVisibilityService | None = None) -> None:
        self.visibility = visibility_service or PortalVisibilityService()

    def get_portal_home_summary(self, person_id: str, client_id: str) -> dict:
        now = datetime.now(timezone.utc)
        today = now.date()
        recent_cutoff = now - timedelta(days=7)

        requests = self.visibility.get_visible_requests(person_id, client_id)
        pending_requests = [item for item in requests if item.status in {"pending", "submitted", "in_review", "rejected", "expired"}]
        overdue_requests = [item for item in pending_requests if item.due_date is not None and item.due_date < today]

        recent_documents = [
            item
            for item in self.visibility.get_visible_documents(person_id, client_id)
            if item.created_at and self._as_utc(item.created_at) >= recent_cutoff
        ]
        open_cases = [
            item
            for item in self.visibility.get_visible_cases(person_id, client_id)
            if item.status not in {"closed", "resolved", "cancelled", "done"}
        ]

        return {
            "pending_requests": self.visibility.count_pending_requests(person_id, client_id),
            "overdue_requests": len(overdue_requests),
            "recent_documents": len(recent_documents),
            "open_cases": len(open_cases),
            "companies_count": self.visibility.count_visible_companies(person_id, client_id),
        }

    def get_portal_home_tasks(self, person_id: str, client_id: str) -> list[dict]:
        requests = self.visibility.get_visible_requests(person_id, client_id)
        actionable = [item for item in requests if item.status in {"pending", "submitted", "in_review", "rejected", "expired"}]
        return self._build_portal_tasks(actionable, datetime.now(timezone.utc).date())

    def get_portal_home_activity(self, person_id: str, client_id: str) -> list[dict]:
        documents = self.visibility.get_visible_documents(person_id, client_id)
        cases = self.visibility.get_visible_cases(person_id, client_id)
        requests = self.visibility.get_visible_requests(person_id, client_id)
        return self._build_portal_activity(documents, cases, requests)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

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
        near_due = sorted([item for item in requests if item.due_date and item.due_date >= today], key=lambda item: item.due_date)
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

            items.append({
                "id": item.id,
                "title": item.title,
                "status": item.status,
                "due_date": item.due_date.isoformat() if item.due_date else None,
                "resolution_type": item.resolution_type,
                "priority": priority,
                "cta_label": cta_label,
                "cta_url": f"/portal/requests/{item.id}",
            })
        return items

    @staticmethod
    def _build_portal_activity(documents, cases, requests: list[PersonRequest]) -> list[dict]:
        activity = []

        for item in documents[:4]:
            activity.append({
                "type": "document",
                "message": f"Nuevo documento disponible: {item.original_filename}",
                "date": item.created_at.isoformat() if item.created_at else None,
                "url": "/portal/documents",
            })

        for item in cases[:4]:
            updated_at = item.updated_at or item.created_at
            activity.append({
                "type": "case",
                "message": f"Expediente actualizado: {item.title}",
                "date": updated_at.isoformat() if updated_at else None,
                "url": "/portal/cases",
            })

        for item in requests[:4]:
            event = "resuelta" if item.status == "resolved" else ("rechazada" if item.status == "rejected" else "actualizada")
            stamp = item.resolved_at if item.status == "resolved" else (item.reviewed_at or item.submitted_at or item.created_at)
            activity.append({
                "type": "request",
                "message": f"Solicitud {event}: {item.title}",
                "date": stamp.isoformat() if stamp else None,
                "url": f"/portal/requests/{item.id}",
            })

        return sorted(activity, key=lambda item: item["date"] or "", reverse=True)[:10]
