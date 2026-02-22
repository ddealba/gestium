import pytest

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
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


def create_company(db_session, client_id: str, name: str = "Acme Co", tax_id: str = "T-123") -> Company:
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


def test_admin_can_add_and_remove_company_access(client, db_session):
    tenant = create_client(db_session, "Tenant A")
    admin = create_user(db_session, tenant.id, "admin@tenant-a.com")
    target = create_user(db_session, tenant.id, "target@tenant-a.com")
    company = create_company(db_session, tenant.id)
    seed_rbac()

    assign_role(db_session, admin, "Admin Cliente")
    assign_access(db_session, admin, company, "admin")

    headers = auth_header_for(admin)
    response = client.post(
        f"/admin/companies/{company.id}/access",
        headers=headers,
        json={"user_id": target.id, "access_level": "viewer"},
    )
    assert response.status_code == 201

    list_response = client.get(f"/admin/companies/{company.id}/access", headers=headers)
    assert list_response.status_code == 200
    assert any(item["user_id"] == target.id for item in list_response.get_json()["items"])

    delete_response = client.delete(f"/admin/companies/{company.id}/access/{target.id}", headers=headers)
    assert delete_response.status_code == 200


def test_viewer_and_operator_cannot_manage_company_access(client, db_session):
    tenant = create_client(db_session, "Tenant A")
    viewer = create_user(db_session, tenant.id, "viewer@tenant-a.com")
    company = create_company(db_session, tenant.id)
    seed_rbac()

    assign_role(db_session, viewer, "Operativo")
    assign_access(db_session, viewer, company, "viewer")

    response = client.post(
        f"/admin/companies/{company.id}/access",
        headers=auth_header_for(viewer),
        json={"user_id": viewer.id, "access_level": "admin"},
    )
    assert response.status_code == 403


def test_cross_tenant_company_access_returns_404(client, db_session):
    tenant_a = create_client(db_session, "Tenant A")
    tenant_b = create_client(db_session, "Tenant B")
    admin_a = create_user(db_session, tenant_a.id, "admin@tenant-a.com")
    user_b = create_user(db_session, tenant_b.id, "user@tenant-b.com")
    company_b = create_company(db_session, tenant_b.id)
    seed_rbac()

    assign_role(db_session, admin_a, "Admin Cliente")

    response = client.post(
        f"/admin/companies/{company_b.id}/access",
        headers=auth_header_for(admin_a),
        json={"user_id": user_b.id, "access_level": "viewer"},
    )
    assert response.status_code == 404
