"""Server-rendered web routes for the /app frontend."""

from datetime import datetime

from flask import Blueprint, redirect, render_template

bp = Blueprint("web", __name__)


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
        "nav_items": [
            {
                "page_id": "dashboard",
                "endpoint": "web.app_dashboard",
                "label": "Dashboard",
                "icon": "ph-squares-four",
                "active": False,
                "badge": None,
            },
            {
                "page_id": "companies",
                "endpoint": "web.app_companies",
                "label": "Empresas",
                "icon": "ph-buildings",
                "active": False,
                "badge": None,
            },
        ],
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


@bp.get("/app/companies/<company_id>/cases")
def app_company_cases(company_id: str):
    """Render cases page for a company."""
    return render_template(
        "pages/cases.html",
        active_nav="companies",
        page_id="companies",
        company_id=company_id,
    )


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
