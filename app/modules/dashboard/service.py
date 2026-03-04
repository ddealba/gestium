"""Service layer for tenant dashboard summary."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from app.modules.dashboard.repository import (
    CASE_STATUS_ORDER,
    DOC_STATUS_ORDER,
    DashboardRepository,
)


class DashboardService:
    """Build dashboard summary payload."""

    def __init__(self, repository: DashboardRepository | None = None) -> None:
        self.repository = repository or DashboardRepository()

    def get_summary(
        self,
        client_id: str,
        user_id: str,
        days: int = 14,
        overdue_limit: int = 8,
        activity_limit: int = 12,
        my_cases_limit: int = 5,
    ) -> dict:
        today = date.today()
        now = datetime.now(timezone.utc)
        days_window = max(days, 1)
        since_ts = now - timedelta(days=days_window)

        total_docs = self.repository.count_total_docs(client_id)
        docs_with_extraction = self.repository.count_docs_with_extraction(client_id)
        docs_no_extraction = max(total_docs - docs_with_extraction, 0)
        extract_coverage_pct = round((docs_with_extraction / total_docs) * 100) if total_docs else 0

        cases_by_status_map = self.repository.cases_by_status(client_id)
        docs_by_status_map = self.repository.docs_by_status(client_id)

        activity_raw = (
            self.repository.case_events_for_activity(client_id, activity_limit)
            + self.repository.documents_for_activity(client_id, activity_limit)
            + self.repository.extractions_for_activity(client_id, activity_limit)
        )
        activity_sorted = sorted(
            activity_raw,
            key=lambda item: item.get("_sort_ts") or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )[: max(activity_limit, 1)]
        activity = [{k: v for k, v in item.items() if k != "_sort_ts"} for item in activity_sorted]

        return {
            "kpis": {
                "active_cases": self.repository.count_active_cases(client_id),
                "overdue_cases": self.repository.count_overdue_cases(client_id, today),
                "docs_pending": self.repository.count_docs_pending(client_id),
                "docs_no_extraction": docs_no_extraction,
                "extract_coverage_pct": extract_coverage_pct,
                "my_cases": self.repository.count_my_active_cases(client_id, user_id),
                "companies_active": self.repository.count_active_companies(client_id),
                "companies_with_open_cases": self.repository.count_companies_with_open_cases(client_id),
                "employees_total": self.repository.count_total_active_employees(client_id),
                "cases_created_last_days": self.repository.count_cases_created_since(client_id, since_ts),
                "docs_uploaded_last_days": self.repository.count_docs_uploaded_since(client_id, since_ts),
                "due_today": self.repository.count_due_today(client_id, today),
            },
            "cases_by_status": {
                "labels": CASE_STATUS_ORDER,
                "values": [int(cases_by_status_map.get(status, 0)) for status in CASE_STATUS_ORDER],
            },
            "docs_by_status": {
                "labels": DOC_STATUS_ORDER,
                "values": [int(docs_by_status_map.get(status, 0)) for status in DOC_STATUS_ORDER],
            },
            "employees_by_company": self.repository.employees_by_company(client_id, limit=6),
            "overdue_cases": self.repository.overdue_cases(client_id, today, overdue_limit),
            "my_cases_list": self.repository.my_cases(client_id, user_id, my_cases_limit),
            "activity": activity,
        }
