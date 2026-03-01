"""Server-rendered web routes for the /app frontend."""

from datetime import datetime

from flask import Blueprint, redirect, render_template

bp = Blueprint("web", __name__)


def _build_nav_items() -> list[dict]:
    """Build default sidebar navigation metadata."""
    return [
        {
            "page_id": "dashboard",
            "endpoint": "web.app_dashboard",
            "label": "Dashboard",
            "icon": "ph-squares-four",
            "active": False,
            "badge": None,
            "scope": "tenant",
        },
        {
            "page_id": "companies",
            "endpoint": "web.app_companies",
            "label": "Empresas",
            "icon": "ph-buildings",
            "active": False,
            "badge": None,
            "scope": "tenant",
        },
        {
            "page_id": "employees",
            "endpoint": "web.app_employees",
            "label": "Empleados",
            "icon": "ph-identification-card",
            "active": False,
            "badge": None,
            "scope": "tenant",
        },
        {
            "page_id": "cases",
            "endpoint": "web.app_cases",
            "label": "Expedientes",
            "icon": "ph-folders",
            "active": False,
            "badge": None,
            "scope": "tenant",
        },
        {
            "page_id": "documents",
            "endpoint": "web.app_documents",
            "label": "Documentos",
            "icon": "ph-files",
            "active": False,
            "badge": None,
            "scope": "tenant",
        },
        {
            "page_id": "admin",
            "label": "Administración",
            "icon": "ph-shield-check",
            "active": False,
            "badge": None,
            "scope": "tenant",
            "children": [
                {
                    "page_id": "admin_users",
                    "endpoint": "web.app_admin_users",
                    "label": "Usuarios",
                    "required_permissions": ["tenant.user.read", "tenant.users.manage"],
                    "scope": "tenant",
                },
                {
                    "page_id": "admin_access",
                    "endpoint": "web.app_admin_access",
                    "label": "Accesos por empresa",
                    "required_permissions": ["acl.read", "acl.manage"],
                    "scope": "tenant",
                },
            ],
        },
        {
            "page_id": "platform",
            "label": "Plataforma",
            "icon": "ph-buildings",
            "active": False,
            "badge": None,
            "scope": "platform",
            "children": [
                {
                    "page_id": "platform_tenants",
                    "endpoint": "web.app_platform_tenants",
                    "label": "Gestorías (Tenants)",
                    "required_permissions": ["platform.super_admin"],
                    "scope": "platform",
                },
                {
                    "page_id": "admin_audit",
                    "endpoint": "web.app_admin_audit",
                    "label": "Auditoría global",
                    "required_permissions": ["platform.super_admin"],
                    "scope": "platform_optional",
                },
            ],
        },
    ]


@bp.app_context_processor
def inject_layout_context() -> dict:
    """Shared layout context for the server-rendered frontend."""
    return {
        "ui_version": "1",
        "current_year": datetime.now().year,
        "tenant_name": "Gestium",
        "user_name": "Usuario",
        "user_role": "Operador",
        "user_initials": "US",
        "notifications_count": 0,
        "nav_items": _build_nav_items(),
    }


@bp.get("/app")
def app_index():
    """Redirect to protected app landing (guard handles unauthenticated users)."""
    return redirect("/app/companies")


@bp.get("/app/login")
def app_login():
    """Render login page."""
    return render_template("pages/login.html")


@bp.get("/app/dashboard")
def app_dashboard():
    """Render dashboard page (optional route)."""
    return render_template("pages/dashboard.html", active_nav="dashboard", page_id="dashboard")


@bp.get("/app/companies")
def app_companies():
    """Render companies page."""
    return render_template("pages/companies.html", active_nav="companies", page_id="companies")


@bp.get("/app/companies/<company_id>/employees")
def app_company_employees(company_id: str):
    """Render employees page for a company."""
    return render_template(
        "pages/employees.html",
        active_nav="companies",
        page_id="companies",
        company_id=company_id,
    )


@bp.get("/app/employees")
def app_employees():
    """Render tenant-level employees page."""
    return render_template("pages/employees.html", active_nav="employees", page_id="employees")


@bp.get("/app/companies/<company_id>/cases")
def app_company_cases(company_id: str):
    """Render cases page for a company."""
    return render_template(
        "pages/cases.html",
        active_nav="companies",
        page_id="companies",
        company_id=company_id,
    )


@bp.get("/app/cases")
def app_cases():
    """Render tenant-level cases page."""
    return render_template("pages/cases.html", active_nav="cases", page_id="cases")


@bp.get("/app/companies/<company_id>/cases/<case_id>")
def app_case_detail(company_id: str, case_id: str):
    """Render case detail page."""
    return render_template(
        "pages/case_detail.html",
        active_nav="companies",
        page_id="companies",
        company_id=company_id,
        case_id=case_id,
    )


@bp.get("/app/documents")
def app_documents():
    """Render tenant-level documents page."""
    return render_template("pages/documentos.html", active_nav="documents", page_id="documents")


@bp.get("/app/admin/users")
def app_admin_users():
    """Render tenant admin users page."""
    return render_template("pages/admin_users.html", active_nav="admin_users", page_id="admin_users")


@bp.get("/app/admin/access")
def app_admin_access():
    """Render tenant admin company access page."""
    return render_template("pages/admin_access.html", active_nav="admin_access", page_id="admin_access")


@bp.get("/app/admin/audit")
def app_admin_audit():
    """Render tenant admin audit page."""
    return render_template("pages/admin_audit.html", active_nav="admin_audit", page_id="admin_audit")


@bp.get("/app/platform/tenants")
def app_platform_tenants():
    """Render super-admin tenant cards page."""
    return render_template(
        "pages/platform_tenants.html",
        active_nav="platform_tenants",
        page_id="platform_tenants",
    )


@bp.get("/app/platform/tenants/new")
def app_platform_tenant_new():
    """Render super-admin create tenant page."""
    return render_template(
        "pages/platform_tenant_new.html",
        active_nav="platform_tenants",
        page_id="platform_tenant_new",
    )


@bp.get("/app/platform/tenants/<tenant_id>")
def app_platform_tenant_detail(tenant_id: str):
    """Render super-admin tenant detail page."""
    return render_template(
        "pages/platform_tenant_detail.html",
        active_nav="platform_tenants",
        page_id="platform_tenant_detail",
        tenant_id=tenant_id,
    )
