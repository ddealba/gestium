import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.case import Case
from app.models.client import Client
from app.models.company import Company
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.models.employee import Employee
from app.models.role import Role
from app.models.user import User
from app.repositories.user_role_repository import UserRoleRepository


@pytest.fixture()
def db_session(app):
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
        db.drop_all()


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.client_id)
    return {"Authorization": f"Bearer {token}"}


def _create_client(name: str) -> Client:
    client = Client(id=str(uuid.uuid4()), name=f"{name}-{uuid.uuid4()}", status="active", plan="basic")
    db.session.add(client)
    db.session.commit()
    return client


def _create_user(client_id: str, email: str) -> User:
    user = User(client_id=client_id, email=email, status="active")
    db.session.add(user)
    db.session.commit()
    return user


def _assign_role(user: User, role_name: str, scope: str = "tenant", client_id: str | None = None):
    resolved_client_id = user.client_id if client_id is None and scope == "tenant" else client_id
    role = Role.query.filter_by(name=role_name, scope=scope, client_id=resolved_client_id).one()
    UserRoleRepository(db.session).assign_role(user.id, role.id)
    db.session.commit()


def test_dashboard_summary_returns_200_for_user_with_permission(client, db_session):
    tenant = _create_client("Tenant Dashboard")
    seed_rbac()

    user = _create_user(tenant.id, "dashboard@example.com")
    _assign_role(user, "Admin Cliente")

    company = Company(client_id=tenant.id, name="Acme", tax_id="A-1")
    db.session.add(company)
    db.session.flush()

    case = Case(
        client_id=tenant.id,
        company_id=company.id,
        type="laboral",
        title="Caso abierto",
        status="open",
        due_date=date.today() - timedelta(days=1),
        created_at=datetime.now(timezone.utc),
        responsible_user_id=user.id,
    )
    db.session.add(case)
    db.session.flush()

    doc = Document(
        client_id=tenant.id,
        company_id=company.id,
        case_id=case.id,
        original_filename="a.pdf",
        content_type="application/pdf",
        storage_path="/tmp/a.pdf",
        status="pending",
    )
    db.session.add(doc)
    db.session.add(
        Employee(
            client_id=tenant.id,
            company_id=company.id,
            full_name="Empleado Uno",
            start_date=date.today() - timedelta(days=5),
            status="active",
        )
    )
    db.session.commit()

    response = client.get("/dashboard/summary", headers=_auth_header(user))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["kpis"]["active_cases"] == 1
    assert payload["kpis"]["docs_pending"] == 1
    assert payload["kpis"]["companies_active"] == 1
    assert payload["kpis"]["companies_with_open_cases"] == 1
    assert payload["kpis"]["employees_total"] == 1
    assert payload["kpis"]["my_cases"] == 1


def test_dashboard_summary_super_admin_without_tenant_context_returns_400(client, db_session):
    tenant = _create_client("Tenant SA")
    seed_rbac()

    user = _create_user(tenant.id, "super.dashboard@example.com")
    _assign_role(user, "Super Admin", scope="platform", client_id=None)

    response = client.get("/dashboard/summary", headers=_auth_header(user))

    assert response.status_code == 400
    assert response.get_json() == {
        "error": {"code": "tenant_context_required", "message": "Selecciona un tenant"}
    }


def test_dashboard_summary_without_permission_returns_403(client, db_session):
    tenant = _create_client("Tenant Restricted")
    seed_rbac()

    user = _create_user(tenant.id, "restricted@example.com")

    response = client.get("/dashboard/summary", headers=_auth_header(user))

    assert response.status_code == 403


def test_dashboard_summary_isolated_by_tenant(client, db_session):
    tenant_a = _create_client("Tenant A")
    tenant_b = _create_client("Tenant B")
    seed_rbac()

    user_a = _create_user(tenant_a.id, "a@example.com")
    _assign_role(user_a, "Admin Cliente")

    company_a = Company(client_id=tenant_a.id, name="Company A", tax_id="TA-1")
    company_b = Company(client_id=tenant_b.id, name="Company B", tax_id="TB-1")
    db.session.add_all([company_a, company_b])
    db.session.flush()

    case_a = Case(
        client_id=tenant_a.id,
        company_id=company_a.id,
        type="x",
        title="A",
        status="open",
        responsible_user_id=user_a.id,
    )
    case_b = Case(client_id=tenant_b.id, company_id=company_b.id, type="x", title="B", status="open")
    db.session.add_all([case_a, case_b])
    db.session.flush()

    doc_b = Document(
        client_id=tenant_b.id,
        company_id=company_b.id,
        case_id=case_b.id,
        original_filename="b.pdf",
        content_type="application/pdf",
        storage_path="/tmp/b.pdf",
        status="pending",
    )
    db.session.add(doc_b)
    db.session.flush()

    extraction_b = DocumentExtraction(
        client_id=tenant_b.id,
        document_id=doc_b.id,
        company_id=company_b.id,
        case_id=case_b.id,
        schema_version="1.0",
        extracted_json={"ok": True},
        status="success",
    )
    db.session.add(extraction_b)

    db.session.add(
        Employee(
            client_id=tenant_b.id,
            company_id=company_b.id,
            full_name="Empleado B",
            start_date=date.today(),
            status="active",
        )
    )
    db.session.commit()

    response = client.get("/dashboard/summary", headers=_auth_header(user_a))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["kpis"]["active_cases"] == 1
    assert payload["kpis"]["docs_pending"] == 0
    assert payload["kpis"]["docs_no_extraction"] == 0
    assert payload["kpis"]["employees_total"] == 0
    assert payload["employees_by_company"] == {"labels": [], "values": []}


def test_dashboard_summary_employees_and_companies_and_my_cases(client, db_session):
    tenant = _create_client("Tenant Metrics")
    seed_rbac()

    user = _create_user(tenant.id, "owner@example.com")
    another_user = _create_user(tenant.id, "other@example.com")
    _assign_role(user, "Admin Cliente")

    company_a = Company(client_id=tenant.id, name="Empresa A", tax_id="M-1", status="active")
    company_b = Company(client_id=tenant.id, name="Empresa B", tax_id="M-2", status="active")
    company_c = Company(client_id=tenant.id, name="Empresa C", tax_id="M-3", status="inactive")
    db.session.add_all([company_a, company_b, company_c])
    db.session.flush()

    db.session.add_all(
        [
            Case(
                client_id=tenant.id,
                company_id=company_a.id,
                type="laboral",
                title="Caso 1",
                status="open",
                responsible_user_id=user.id,
                due_date=date.today() + timedelta(days=2),
            ),
            Case(
                client_id=tenant.id,
                company_id=company_b.id,
                type="laboral",
                title="Caso 2",
                status="in_progress",
                responsible_user_id=user.id,
                due_date=date.today() + timedelta(days=1),
            ),
            Case(
                client_id=tenant.id,
                company_id=company_b.id,
                type="laboral",
                title="Caso 3",
                status="waiting",
                responsible_user_id=another_user.id,
            ),
            Case(
                client_id=tenant.id,
                company_id=company_c.id,
                type="laboral",
                title="Caso Cerrado",
                status="done",
                responsible_user_id=user.id,
            ),
        ]
    )

    db.session.add_all(
        [
            Employee(client_id=tenant.id, company_id=company_a.id, full_name="A1", start_date=date.today(), status="active"),
            Employee(client_id=tenant.id, company_id=company_a.id, full_name="A2", start_date=date.today(), status="active"),
            Employee(client_id=tenant.id, company_id=company_b.id, full_name="B1", start_date=date.today(), status="active"),
            Employee(client_id=tenant.id, company_id=company_c.id, full_name="C1", start_date=date.today(), status="terminated", end_date=date.today()),
        ]
    )
    db.session.commit()

    response = client.get("/dashboard/summary", headers=_auth_header(user))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["kpis"]["my_cases"] == 2
    assert payload["kpis"]["companies_active"] == 2
    assert payload["kpis"]["companies_with_open_cases"] == 2
    assert payload["kpis"]["employees_total"] == 3
    assert payload["employees_by_company"]["labels"] == ["Empresa A", "Empresa B", "Empresa C"]
    assert payload["employees_by_company"]["values"] == [2, 1, 1]
    assert [item["title"] for item in payload["my_cases_list"]] == ["Caso 2", "Caso 1"]


def test_dashboard_summary_my_cases_empty(client, db_session):
    tenant = _create_client("Tenant Empty Cases")
    seed_rbac()

    user = _create_user(tenant.id, "empty@example.com")
    _assign_role(user, "Admin Cliente")

    company = Company(client_id=tenant.id, name="Empresa", tax_id="E-1", status="active")
    db.session.add(company)
    db.session.flush()

    db.session.add(
        Case(
            client_id=tenant.id,
            company_id=company.id,
            type="laboral",
            title="Caso de otro usuario",
            status="open",
            responsible_user_id=str(uuid.uuid4()),
        )
    )
    db.session.commit()

    response = client.get("/dashboard/summary", headers=_auth_header(user))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["kpis"]["my_cases"] == 0
    assert payload["my_cases_list"] == []
