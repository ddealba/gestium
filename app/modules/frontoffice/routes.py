"""Frontoffice routes (/portal)."""

from __future__ import annotations

from flask import Blueprint, g, render_template, request

from app.common.decorators import auth_required, require_user_type
from app.common.jwt import create_access_token
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.modules.audit.audit_service import AuditService
from app.modules.auth.service import AuthService
from app.modules.frontoffice.service import FrontofficeService
from app.modules.person_request.request_schemas import PersonRequestResponseSchema
from app.modules.person_request.request_service import PersonRequestService

bp = Blueprint("frontoffice", __name__)


@bp.get("/portal/login")
def portal_login_page():
    return render_template("frontoffice/login.html")


@bp.post("/portal/login")
def portal_login():
    payload = request.get_json(silent=True) or request.form.to_dict() or {}
    email = payload.get("email")
    password = payload.get("password")
    client_id = payload.get("client_id")

    service = AuthService()
    user_id, resolved_client_id = service.authenticate(email, password, client_id, "portal")
    token = create_access_token(user_id, resolved_client_id)

    AuditService().log_action(
        client_id=str(resolved_client_id),
        actor_user_id=str(user_id),
        action="portal_login",
        entity_type="portal_session",
        entity_id=str(user_id),
        metadata={"path": request.path, "method": request.method},
    )

    return ok(
        {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600,
        }
    )


@bp.get("/portal")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_home():
    payload = FrontofficeService().get_portal_home(g.user, str(g.client_id))
    return render_template("frontoffice/home.html", home=payload)


@bp.get("/portal/profile")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_profile():
    service = FrontofficeService()
    profile = service.get_portal_profile(g.user, str(g.client_id))
    AuditService().log_action(
        client_id=str(g.client_id),
        actor_user_id=str(g.user.id),
        action="portal_profile_viewed",
        entity_type="person",
        entity_id=str(g.user.person_id),
    )
    return render_template("frontoffice/profile.html", profile=profile)


@bp.get("/portal/documents")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_documents():
    service = FrontofficeService()
    documents_person = service.get_portal_documents(g.user, str(g.client_id), section="person")
    documents_employee = service.get_portal_documents(g.user, str(g.client_id), section="employee")
    documents_company = service.get_portal_documents(g.user, str(g.client_id), section="company")
    return render_template(
        "frontoffice/documents.html",
        documents_person=documents_person,
        documents_employee=documents_employee,
        documents_company=documents_company,
    )


@bp.get("/portal/cases")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_cases():
    service = FrontofficeService()
    cases_person = service.get_portal_cases(g.user, str(g.client_id), section="person")
    cases_company = service.get_portal_cases(g.user, str(g.client_id), section="company")
    return render_template(
        "frontoffice/cases.html",
        cases_person=cases_person,
        cases_company=cases_company,
    )


@bp.get("/portal/requests")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_requests():
    items = PersonRequestService().portal_list_requests(g.user, str(g.client_id))
    return render_template("frontoffice/requests.html", requests=items)


@bp.get("/portal/requests/<request_id>")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_request_detail(request_id: str):
    item = PersonRequestService().portal_get_request(g.user, str(g.client_id), request_id)
    return render_template("frontoffice/request_detail.html", request_item=PersonRequestResponseSchema.dump(item))


@bp.get("/portal/companies")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_companies():
    service = FrontofficeService()
    companies = service.get_portal_companies(g.user, str(g.client_id))
    return render_template("frontoffice/companies.html", companies=companies)


@bp.get("/portal/companies/<company_id>")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_company_detail(company_id: str):
    service = FrontofficeService()
    company = service.get_portal_company_detail(g.user, str(g.client_id), company_id)
    documents = service.get_portal_documents(g.user, str(g.client_id), section="company")
    cases = service.get_portal_cases(g.user, str(g.client_id), section="company")
    return render_template(
        "frontoffice/company_detail.html",
        company=company,
        documents=[doc for doc in documents if doc["company_id"] == company_id][:10],
        cases=[case for case in cases if case["company_id"] == company_id][:10],
    )


@bp.get("/portal/api/me")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_api_me():
    payload = FrontofficeService().get_portal_profile(g.user, str(g.client_id))
    return ok(payload)




@bp.get("/portal/api/home")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_api_home():
    payload = FrontofficeService().get_portal_home(g.user, str(g.client_id))
    return ok(payload)


@bp.get("/portal/api/summary")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_api_summary():
    payload = FrontofficeService().get_portal_summary(g.user, str(g.client_id))
    return ok(payload)


@bp.get("/portal/api/documents")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_api_documents():
    scope = request.args.get("scope")
    payload = FrontofficeService().get_portal_documents(g.user, str(g.client_id), section=scope)
    return ok(payload)


@bp.get("/portal/api/cases")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_api_cases():
    scope = request.args.get("scope")
    payload = FrontofficeService().get_portal_cases(g.user, str(g.client_id), section=scope)
    return ok(payload)


@bp.get("/portal/api/companies")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_api_companies():
    payload = FrontofficeService().get_portal_companies(g.user, str(g.client_id))
    AuditService().log_action(
        client_id=str(g.client_id),
        actor_user_id=str(g.user.id),
        action="portal_company_viewed",
        entity_type="person",
        entity_id=str(g.user.person_id),
    )
    return ok(payload)


@bp.get("/portal/api/companies/<company_id>")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_api_company_detail(company_id: str):
    payload = FrontofficeService().get_portal_company_detail(g.user, str(g.client_id), company_id)
    return ok(payload)


@bp.get("/portal/api/companies/<company_id>/documents")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_api_company_documents(company_id: str):
    service = FrontofficeService()
    service.get_portal_company_detail(g.user, str(g.client_id), company_id)
    payload = service.get_portal_documents(g.user, str(g.client_id), section="company")
    AuditService().log_action(
        client_id=str(g.client_id),
        actor_user_id=str(g.user.id),
        action="portal_company_documents_viewed",
        entity_type="company",
        entity_id=str(company_id),
    )
    return ok([item for item in payload if item["company_id"] == company_id])


@bp.get("/portal/api/companies/<company_id>/cases")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_api_company_cases(company_id: str):
    service = FrontofficeService()
    service.get_portal_company_detail(g.user, str(g.client_id), company_id)
    payload = service.get_portal_cases(g.user, str(g.client_id), section="company")
    AuditService().log_action(
        client_id=str(g.client_id),
        actor_user_id=str(g.user.id),
        action="portal_company_cases_viewed",
        entity_type="company",
        entity_id=str(company_id),
    )
    return ok([item for item in payload if item["company_id"] == company_id])


@bp.get("/portal/api/my-documents")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_api_documents_legacy():
    payload = FrontofficeService().get_portal_documents(g.user, str(g.client_id))
    return ok(payload)


@bp.get("/portal/api/my-cases")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_api_cases_legacy():
    payload = FrontofficeService().get_portal_cases(g.user, str(g.client_id))
    return ok(payload)


@bp.get("/portal/api/my-companies")
@auth_required
@tenant_required
@require_user_type("portal")
def portal_api_companies_legacy():
    payload = FrontofficeService().get_portal_companies(g.user, str(g.client_id))
    return ok(payload)
