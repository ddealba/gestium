import pytest

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.case_event import CaseEvent
from app.models.client import Client
from app.models.company import Company
from app.models.role import Role
from app.models.user import User
from app.repositories.user_company_access_repository import UserCompanyAccessRepository
from app.repositories.user_role_repository import UserRoleRepository


@pytest.fixture()
def db_session(app):
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
        db.drop_all()


def create_client(db_session, name: str) -> Client:
    client = Client(name=name)
    db_session.add(client)
    db_session.commit()
    return client


def create_user(db_session, client_id: str, email: str) -> User:
    user = User(client_id=client_id, email=email, status="active")
    db_session.add(user)
    db_session.commit()
    return user


def create_company(db_session, client_id: str, name: str, tax_id: str) -> Company:
    company = Company(client_id=client_id, name=name, tax_id=tax_id)
    db_session.add(company)
    db_session.commit()
    return company


def auth_header_for(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.client_id)
    return {"Authorization": f"Bearer {token}"}


def assign_role(db_session, user: User, role_name: str) -> None:
    role = Role.query.filter_by(name=role_name, scope="tenant", client_id=user.client_id).one()
    UserRoleRepository(db_session).assign_role(user.id, role.id)
    db_session.commit()


def assign_access(db_session, user: User, company: Company, level: str) -> None:
    UserCompanyAccessRepository(db_session).upsert_access(user.id, company.id, user.client_id, level)
    db_session.commit()


def test_viewer_operator_events_and_acl(client, db_session):
    tenant_a = create_client(db_session, "Tenant A")
    company_a = create_company(db_session, tenant_a.id, "Company A", "A-001")
    viewer = create_user(db_session, tenant_a.id, "viewerA@example.com")
    operator = create_user(db_session, tenant_a.id, "operatorA@example.com")
    seed_rbac()

    assign_role(db_session, viewer, "Admin Cliente")
    assign_role(db_session, operator, "Asesor")
    assign_access(db_session, viewer, company_a, "viewer")
    assign_access(db_session, operator, company_a, "operator")

    list_response = client.get(f"/companies/{company_a.id}/cases", headers=auth_header_for(viewer))
    assert list_response.status_code == 200

    viewer_create_response = client.post(
        f"/companies/{company_a.id}/cases",
        headers=auth_header_for(viewer),
        json={"type": "laboral", "title": "No permitido"},
    )
    assert viewer_create_response.status_code in (403, 404)

    operator_create_response = client.post(
        f"/companies/{company_a.id}/cases",
        headers=auth_header_for(operator),
        json={"type": "laboral", "title": "Caso permitido", "description": "Detalle"},
    )
    assert operator_create_response.status_code == 201
    case_id = operator_create_response.get_json()["case"]["id"]

    events = CaseEvent.query.filter_by(case_id=case_id).all()
    assert len(events) >= 1

    comment_response = client.post(
        f"/companies/{company_a.id}/cases/{case_id}/events/comment",
        headers=auth_header_for(operator),
        json={"comment": "Seguimiento inicial"},
    )
    assert comment_response.status_code == 201


def test_cross_tenant_isolation_and_status_change_rbac_acl(client, db_session):
    tenant_a = create_client(db_session, "Tenant A")
    tenant_b = create_client(db_session, "Tenant B")
    company_a = create_company(db_session, tenant_a.id, "Company A", "A-001")
    company_b = create_company(db_session, tenant_b.id, "Company B", "B-001")

    admin_a = create_user(db_session, tenant_a.id, "adminA@example.com")
    admin_b = create_user(db_session, tenant_b.id, "adminB@example.com")
    asesor_a = create_user(db_session, tenant_a.id, "asesorA@example.com")

    seed_rbac()

    assign_role(db_session, admin_a, "Admin Cliente")
    assign_role(db_session, admin_b, "Admin Cliente")
    assign_role(db_session, asesor_a, "Asesor")

    assign_access(db_session, admin_a, company_a, "admin")
    assign_access(db_session, admin_b, company_b, "admin")
    assign_access(db_session, asesor_a, company_a, "manager")

    create_case_response = client.post(
        f"/companies/{company_a.id}/cases",
        headers=auth_header_for(admin_a),
        json={"type": "laboral", "title": "Caso tenant A"},
    )
    assert create_case_response.status_code == 201
    case_id = create_case_response.get_json()["case"]["id"]

    cross_tenant_get_response = client.get(
        f"/companies/{company_a.id}/cases/{case_id}",
        headers=auth_header_for(admin_b),
    )
    assert cross_tenant_get_response.status_code == 404

    no_permission_status_response = client.post(
        f"/companies/{company_a.id}/cases/{case_id}/status",
        headers=auth_header_for(asesor_a),
        json={"status": "in_progress"},
    )
    assert no_permission_status_response.status_code == 403

    allowed_status_response = client.post(
        f"/companies/{company_a.id}/cases/{case_id}/status",
        headers=auth_header_for(admin_a),
        json={"status": "in_progress"},
    )
    assert allowed_status_response.status_code == 200

    status_events = CaseEvent.query.filter_by(case_id=case_id, event_type="status_change").all()
    assert len(status_events) >= 2
