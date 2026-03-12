"""Portal routes (/portal and /portal/api)."""

from __future__ import annotations

from flask import Blueprint, g, render_template, request

from app.common.decorators import auth_required, portal_user_required
from app.common.jwt import create_access_token
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.modules.auth.service import AuthService
from app.modules.person_request.request_schemas import PersonRequestResponseSchema
from app.modules.person_request.request_service import PersonRequestService
from app.modules.portal.portal_audit_service import PortalAuditService
from app.modules.portal.context import PortalContext
from app.modules.portal.portal_service import PortalService

bp = Blueprint("portal", __name__)


def _portal_context() -> PortalContext:
    return PortalContext.from_user(g.user, str(g.client_id))


@bp.get("/portal/login")
def portal_login_page():
    return render_template("frontoffice/login.html")


@bp.post("/portal/login")
def portal_login():
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    email = payload.get("email")
    password = payload.get("password")
    client_id = payload.get("client_id")

    user_id, resolved_client_id = AuthService().authenticate(email, password, client_id, "portal")
    token = create_access_token(user_id, resolved_client_id)

    PortalAuditService().log(
        action="portal_login",
        context=PortalContext(user_id=str(user_id), person_id="", client_id=str(resolved_client_id)),
        entity_type="portal_session",
        entity_id=str(user_id),
        metadata={"path": request.path, "method": request.method},
    )

    return ok({"access_token": token, "token_type": "Bearer", "expires_in": 3600})


@bp.get("/portal")
@auth_required
@tenant_required
@portal_user_required
def portal_home():
    payload = PortalService().get_portal_home(_portal_context())
    return render_template("frontoffice/home.html", home=payload)


@bp.get("/portal/profile")
@auth_required
@tenant_required
@portal_user_required
def portal_profile():
    context = _portal_context()
    profile = PortalService().get_portal_profile(context)
    PortalAuditService().log("portal_profile_viewed", context, "person", context.person_id)
    return render_template("frontoffice/profile.html", profile=profile)


@bp.get("/portal/documents")
@auth_required
@tenant_required
@portal_user_required
def portal_documents():
    context = _portal_context()
    service = PortalService()
    documents_person = service.get_portal_documents(context, scope="person")
    documents_employee = service.get_portal_documents(context, scope="employee")
    documents_company = service.get_portal_documents(context, scope="company")
    return render_template(
        "frontoffice/documents.html",
        documents_person=documents_person,
        documents_employee=documents_employee,
        documents_company=documents_company,
    )


@bp.get("/portal/cases")
@auth_required
@tenant_required
@portal_user_required
def portal_cases():
    context = _portal_context()
    service = PortalService()
    cases_person = service.get_portal_cases(context, scope="person")
    cases_company = service.get_portal_cases(context, scope="company")
    return render_template("frontoffice/cases.html", cases_person=cases_person, cases_company=cases_company)


@bp.get("/portal/requests")
@auth_required
@tenant_required
@portal_user_required
def portal_requests():
    context = _portal_context()
    items = PersonRequestService().portal_list_requests(g.user, context.client_id)
    return render_template("frontoffice/requests.html", requests=items)


@bp.get("/portal/requests/<request_id>")
@auth_required
@tenant_required
@portal_user_required
def portal_request_detail(request_id: str):
    context = _portal_context()
    item = PersonRequestService().portal_get_request(g.user, context.client_id, request_id)
    return render_template("frontoffice/request_detail.html", request_item=PersonRequestResponseSchema.dump(item))


@bp.get("/portal/companies")
@auth_required
@tenant_required
@portal_user_required
def portal_companies():
    companies = PortalService().get_portal_companies(_portal_context())
    return render_template("frontoffice/companies.html", companies=companies)


@bp.get("/portal/companies/<company_id>")
@auth_required
@tenant_required
@portal_user_required
def portal_company_detail(company_id: str):
    context = _portal_context()
    service = PortalService()
    company = service.get_portal_company_detail(context, company_id)
    documents = service.get_portal_documents(context, scope="company")
    cases = service.get_portal_cases(context, scope="company")
    return render_template(
        "frontoffice/company_detail.html",
        company=company,
        documents=[doc for doc in documents if doc["company_id"] == company_id][:10],
        cases=[case for case in cases if case["company_id"] == company_id][:10],
    )


@bp.get("/portal/api/me")
@auth_required
@tenant_required
@portal_user_required
def portal_api_me():
    return ok(PortalService().get_portal_profile(_portal_context()))


@bp.get("/portal/api/home")
@auth_required
@tenant_required
@portal_user_required
def portal_api_home():
    return ok(PortalService().get_portal_home(_portal_context()))


@bp.get("/portal/api/summary")
@auth_required
@tenant_required
@portal_user_required
def portal_api_summary():
    return ok(PortalService().get_portal_summary(_portal_context()))


@bp.get("/portal/api/documents")
@auth_required
@tenant_required
@portal_user_required
def portal_api_documents():
    return ok(PortalService().get_portal_documents(_portal_context(), scope=request.args.get("scope")))


@bp.get("/portal/api/cases")
@auth_required
@tenant_required
@portal_user_required
def portal_api_cases():
    return ok(PortalService().get_portal_cases(_portal_context(), scope=request.args.get("scope")))


@bp.get("/portal/api/companies")
@auth_required
@tenant_required
@portal_user_required
def portal_api_companies():
    context = _portal_context()
    payload = PortalService().get_portal_companies(context)
    PortalAuditService().log("portal_company_viewed", context, "person", context.person_id)
    return ok(payload)


@bp.get("/portal/api/companies/<company_id>")
@auth_required
@tenant_required
@portal_user_required
def portal_api_company_detail(company_id: str):
    context = _portal_context()
    payload = PortalService().get_portal_company_detail(context, company_id)
    PortalAuditService().log("portal_company_viewed", context, "company", company_id)
    return ok(payload)


@bp.get("/portal/api/companies/<company_id>/documents")
@auth_required
@tenant_required
@portal_user_required
def portal_api_company_documents(company_id: str):
    context = _portal_context()
    service = PortalService()
    service.get_portal_company_detail(context, company_id)
    payload = service.get_portal_documents(context, scope="company")
    PortalAuditService().log("portal_document_viewed", context, "company", company_id)
    return ok([item for item in payload if item["company_id"] == company_id])


@bp.get("/portal/api/companies/<company_id>/cases")
@auth_required
@tenant_required
@portal_user_required
def portal_api_company_cases(company_id: str):
    context = _portal_context()
    service = PortalService()
    service.get_portal_company_detail(context, company_id)
    payload = service.get_portal_cases(context, scope="company")
    PortalAuditService().log("portal_case_viewed", context, "company", company_id)
    return ok([item for item in payload if item["company_id"] == company_id])


@bp.get("/portal/api/my-documents")
@auth_required
@tenant_required
@portal_user_required
def portal_api_documents_legacy():
    return ok(PortalService().get_portal_documents(_portal_context()))


@bp.get("/portal/api/my-cases")
@auth_required
@tenant_required
@portal_user_required
def portal_api_cases_legacy():
    return ok(PortalService().get_portal_cases(_portal_context()))


@bp.get("/portal/api/my-companies")
@auth_required
@tenant_required
@portal_user_required
def portal_api_companies_legacy():
    return ok(PortalService().get_portal_companies(_portal_context()))
