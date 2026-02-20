"""Service layer for case operations."""

from __future__ import annotations

from datetime import date

from werkzeug.exceptions import BadRequest, NotFound

from app.models.case import Case
from app.models.case_event import CaseEvent
from app.modules.cases.repository import CaseEventRepository, CaseRepository
from app.modules.companies.repository import CompanyRepository

TERMINAL_CASE_STATUSES = {"done", "cancelled"}


class CaseService:
    """Case service for case and case-event business rules."""

    def __init__(
        self,
        repository: CaseRepository | None = None,
        event_repository: CaseEventRepository | None = None,
        company_repository: CompanyRepository | None = None,
    ) -> None:
        self.repository = repository or CaseRepository()
        self.event_repository = event_repository or CaseEventRepository()
        self.company_repository = company_repository or CompanyRepository()

    def list_company_cases(
        self,
        client_id: str,
        company_id: str,
        user_id: str,
        status: str | None = None,
        q: str | None = None,
        sort: str | None = None,
        order: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Case]:
        del user_id
        self._ensure_company(client_id, company_id)
        return self.repository.list_by_company(
            company_id=company_id,
            client_id=client_id,
            status=status,
            q=q,
            sort=sort,
            order=order,
            limit=limit,
            offset=offset,
        )

    def create_case(
        self,
        client_id: str,
        company_id: str,
        actor_user_id: str,
        payload: dict,
    ) -> Case:
        self._ensure_company(client_id, company_id)

        title = self._require_str(payload.get("title"), "title_required")
        case_type = self._optional_str(payload.get("type")) or "general"
        description = self._optional_str(payload.get("description"))
        due_date = self._coerce_due_date(payload.get("due_date"))
        responsible_user_id = self._optional_str(payload.get("responsible_user_id"))

        case = Case(
            client_id=client_id,
            company_id=company_id,
            title=title,
            type=case_type,
            description=description,
            due_date=due_date,
            responsible_user_id=responsible_user_id,
            status="open",
        )
        self.repository.create(case)

        initial_comment = self._optional_str(payload.get("comment"))
        if initial_comment:
            self.event_repository.create(
                CaseEvent(
                    client_id=client_id,
                    company_id=company_id,
                    case_id=case.id,
                    actor_user_id=actor_user_id,
                    event_type="comment",
                    payload={"comment": initial_comment},
                )
            )
        else:
            self.event_repository.create(
                CaseEvent(
                    client_id=client_id,
                    company_id=company_id,
                    case_id=case.id,
                    actor_user_id=actor_user_id,
                    event_type="status_change",
                    payload={"from": None, "to": "open"},
                )
            )

        return case

    def get_case(self, client_id: str, company_id: str, case_id: str) -> Case:
        self._ensure_company(client_id, company_id)
        case = self.repository.get_by_id(case_id, client_id)
        if case is None or case.company_id != company_id:
            raise NotFound("Case not found.")
        return case

    def update_case(self, client_id: str, company_id: str, case_id: str, payload: dict) -> Case:
        case = self.get_case(client_id, company_id, case_id)

        if "title" in payload:
            case.title = self._require_str(payload.get("title"), "title_required")
        if "description" in payload:
            case.description = self._optional_str(payload.get("description"))
        if "type" in payload:
            case.type = self._require_str(payload.get("type"), "type_required")
        if "due_date" in payload:
            case.due_date = self._coerce_due_date(payload.get("due_date"))

        if not {"title", "description", "type", "due_date"}.intersection(payload.keys()):
            raise BadRequest("no_fields_to_update")

        self.repository.update(case)
        return case

    def change_status(
        self,
        client_id: str,
        company_id: str,
        case_id: str,
        actor_user_id: str,
        new_status: str,
    ) -> Case:
        case = self.get_case(client_id, company_id, case_id)
        target_status = self._require_str(new_status, "status_required")

        if case.status in TERMINAL_CASE_STATUSES and target_status != case.status:
            raise BadRequest("invalid_status_transition")

        previous_status = case.status
        case.status = target_status
        self.repository.update(case)
        self.event_repository.create(
            CaseEvent(
                client_id=client_id,
                company_id=company_id,
                case_id=case.id,
                actor_user_id=actor_user_id,
                event_type="status_change",
                payload={"from": previous_status, "to": target_status},
            )
        )
        return case

    def assign_responsible(
        self,
        client_id: str,
        company_id: str,
        case_id: str,
        actor_user_id: str,
        responsible_user_id: str | None,
    ) -> Case:
        case = self.get_case(client_id, company_id, case_id)
        case.responsible_user_id = self._optional_str(responsible_user_id)
        self.repository.update(case)

        self.event_repository.create(
            CaseEvent(
                client_id=client_id,
                company_id=company_id,
                case_id=case.id,
                actor_user_id=actor_user_id,
                event_type="assignment",
                payload={"responsible_user_id": case.responsible_user_id},
            )
        )
        return case

    def list_case_events(
        self,
        client_id: str,
        company_id: str,
        case_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CaseEvent]:
        case = self.get_case(client_id, company_id, case_id)
        return self.event_repository.list_by_case(
            case_id=case.id,
            client_id=client_id,
            limit=limit,
            offset=offset,
        )

    def add_comment(
        self,
        client_id: str,
        company_id: str,
        case_id: str,
        actor_user_id: str,
        comment: str,
    ) -> CaseEvent:
        case = self.get_case(client_id, company_id, case_id)
        comment_value = self._require_str(comment, "comment_required")

        event = CaseEvent(
            client_id=client_id,
            company_id=company_id,
            case_id=case.id,
            actor_user_id=actor_user_id,
            event_type="comment",
            payload={"comment": comment_value},
        )
        return self.event_repository.create(event)

    def _ensure_company(self, client_id: str, company_id: str) -> None:
        company = self.company_repository.get_by_id(company_id, client_id)
        if company is None:
            raise NotFound("Company not found.")

    @staticmethod
    def _optional_str(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            return None
        return normalized

    @classmethod
    def _require_str(cls, value: str | None, error_code: str) -> str:
        normalized = cls._optional_str(value)
        if normalized is None:
            raise BadRequest(error_code)
        return normalized

    @staticmethod
    def _coerce_due_date(raw_value: str | date | None) -> date | None:
        if raw_value is None or raw_value == "":
            return None
        if isinstance(raw_value, date):
            return raw_value
        try:
            return date.fromisoformat(str(raw_value))
        except ValueError as exc:
            raise BadRequest("invalid_due_date") from exc
