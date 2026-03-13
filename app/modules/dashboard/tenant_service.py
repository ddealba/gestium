"""Operational tenant dashboard service."""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.modules.dashboard.repository import DashboardRepository


class DashboardTenantService:
    """Build operational dashboard payload for tenant backoffice."""

    def __init__(self, repository: DashboardRepository | None = None) -> None:
        self.repository = repository or DashboardRepository()

    def get_dashboard_kpis(self, client_id: str) -> dict:
        today = date.today()
        return {
            "persons_total": self.repository.count_persons(client_id),
            "persons_active": self.repository.count_persons_active(client_id),
            "persons_incomplete": self.repository.count_persons_incomplete(client_id),
            "requests_pending": self.repository.count_pending_requests(client_id),
            "requests_overdue": self.repository.count_overdue_requests(client_id, today),
            "requests_submitted_today": self.repository.count_requests_submitted_today(client_id, today),
            "documents_today": self.repository.count_documents_today(client_id, today),
            "documents_pending_processing": self.repository.count_docs_pending(client_id),
            "cases_open": self.repository.count_cases_open(client_id),
            "cases_overdue": self.repository.count_overdue_cases(client_id, today),
        }

    def get_attention_persons(self, client_id: str) -> list[dict]:
        return self.repository.attention_persons(client_id, date.today())

    def get_pending_requests(self, client_id: str) -> list[dict]:
        return self.repository.pending_requests(client_id, date.today())

    def get_recent_activity(self, client_id: str) -> list[dict]:
        activity_raw = (
            self.repository.case_events_for_activity(client_id, 15)
            + self.repository.documents_for_activity(client_id, 15)
            + self.repository.extractions_for_activity(client_id, 15)
        )
        sorted_items = sorted(
            activity_raw,
            key=lambda item: item.get("_sort_ts") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )[:15]
        return [
            {
                "date": item.get("ts"),
                "person_id": None,
                "person_name": None,
                "action": item.get("kind"),
                "entity": item.get("title"),
                "company_id": item.get("company_id"),
                "case_id": item.get("case_id"),
                "document_id": item.get("document_id"),
            }
            for item in sorted_items
        ]

    def get_recent_documents(self, client_id: str) -> list[dict]:
        return self.repository.recent_documents(client_id)

    def get_cases_needing_attention(self, client_id: str) -> list[dict]:
        return self.repository.cases_needing_attention(client_id, date.today())

    def get_dashboard(self, client_id: str) -> dict:
        return {
            "kpis": self.get_dashboard_kpis(client_id),
            "attention_persons": self.get_attention_persons(client_id),
            "pending_requests": self.get_pending_requests(client_id),
            "recent_activity": self.get_recent_activity(client_id),
            "recent_documents": self.get_recent_documents(client_id),
            "cases_attention": self.get_cases_needing_attention(client_id),
        }
