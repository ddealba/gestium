"""Portal service layer."""

from __future__ import annotations

from werkzeug.exceptions import Forbidden, NotFound

from app.extensions import db
from app.models.company import Company
from app.models.person import Person
from app.modules.frontoffice.schemas import serialize_case, serialize_company_relation, serialize_document, serialize_profile
from app.modules.portal.context import PortalContext
from app.modules.portal.dashboard_service import PortalDashboardService
from app.modules.portal.visibility_service import PortalVisibilityService


class PortalService:
    """Provides person-scoped portal reads."""

    def __init__(self) -> None:
        self.visibility = PortalVisibilityService()
        self.dashboard = PortalDashboardService(self.visibility)

    def get_portal_profile(self, context: PortalContext) -> dict:
        person = db.session.query(Person).filter(Person.id == context.person_id, Person.client_id == context.client_id).one_or_none()
        if person is None:
            raise NotFound("person_not_found")
        return serialize_profile(person)

    def get_portal_documents(self, context: PortalContext, scope: str | None = None) -> list[dict]:
        rows = self.visibility.get_visible_documents(context.person_id, context.client_id, scope)
        return [serialize_document(item, scope) for item in rows]

    def get_portal_cases(self, context: PortalContext, scope: str | None = None) -> list[dict]:
        rows = self.visibility.get_visible_cases(context.person_id, context.client_id, scope)
        return [serialize_case(item, scope) for item in rows]

    def get_portal_companies(self, context: PortalContext) -> list[dict]:
        rows = self.visibility.get_visible_companies(context.person_id, context.client_id)
        return [serialize_company_relation(item) for item in rows]

    def get_portal_company_detail(self, context: PortalContext, company_id: str) -> dict:
        if not self.visibility.company_is_visible(context.person_id, context.client_id, company_id):
            raise Forbidden("portal_company_forbidden")

        company = db.session.query(Company).filter(Company.id == company_id, Company.client_id == context.client_id).one_or_none()
        if company is None:
            raise NotFound("company_not_found")

        return {"company_id": company.id, "name": company.name, "tax_id": company.tax_id, "status": company.status}

    def get_portal_summary(self, context: PortalContext) -> dict:
        return {
            "person_documents": self.visibility.count_visible_documents(context.person_id, context.client_id, scope="person"),
            "employee_documents": self.visibility.count_visible_documents(context.person_id, context.client_id, scope="employee"),
            "company_documents": self.visibility.count_visible_documents(context.person_id, context.client_id, scope="company"),
            "personal_cases": self.visibility.count_visible_cases(context.person_id, context.client_id, scope="person"),
            "company_cases": self.visibility.count_visible_cases(context.person_id, context.client_id, scope="company"),
            "companies_count": self.visibility.count_visible_companies(context.person_id, context.client_id),
            "has_employee_scope": len(self.visibility.get_visible_employee_ids(context.person_id, context.client_id)) > 0,
            "has_company_scope": self.visibility.count_visible_companies(context.person_id, context.client_id) > 0,
        }

    def get_portal_home(self, context: PortalContext) -> dict:
        companies = self.get_portal_companies(context)
        employee_ids = self.visibility.get_visible_employee_ids(context.person_id, context.client_id)
        return {
            "summary": self.dashboard.get_portal_home_summary(context.person_id, context.client_id),
            "tasks": self.dashboard.get_portal_home_tasks(context.person_id, context.client_id),
            "activity": self.dashboard.get_portal_home_activity(context.person_id, context.client_id),
            "contexts": {
                "has_personal_area": True,
                "has_employee_area": len(employee_ids) > 0,
                "has_company_area": len(companies) > 0,
            },
            "companies": companies,
        }
