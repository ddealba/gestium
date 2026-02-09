"""Server-rendered web routes for the /app frontend."""

from flask import Blueprint, redirect, render_template

bp = Blueprint("web", __name__)


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
    return render_template("pages/dashboard.html", active_nav="dashboard")


@bp.get("/app/companies")
def app_companies():
    """Render companies page."""
    return render_template("pages/companies.html", active_nav="companies")


@bp.get("/app/companies/<company_id>/employees")
def app_company_employees(company_id: str):
    """Render employees page for a company."""
    return render_template(
        "pages/employees.html",
        active_nav="companies",
        company_id=company_id,
    )
