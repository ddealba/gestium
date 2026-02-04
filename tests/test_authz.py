import pytest

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.client import Client
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


def create_client(db_session) -> Client:
    client = Client(name="Acme")
    db_session.add(client)
    db_session.commit()
    return client


def create_user(db_session, client_id: str, email: str = "user@example.com") -> User:
    user = User(client_id=client_id, email=email, status="active")
    db_session.add(user)
    db_session.commit()
    return user


def auth_header_for(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.client_id)
    return {"Authorization": f"Bearer {token}"}


def test_admin_cliente_can_access_company_write(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()

    admin_role = Role.query.filter_by(name="Admin Cliente", scope="tenant", client_id=tenant.id).one()
    UserRoleRepository(db_session).assign_role(user.id, admin_role.id)
    db_session.commit()

    response = client.get("/rbac/probe/company-write", headers=auth_header_for(user))

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}

    permissions_response = client.get("/rbac/me/permissions", headers=auth_header_for(user))
    assert permissions_response.status_code == 200
    assert "company.write" in permissions_response.get_json()["permissions"]


def test_user_without_roles_gets_forbidden(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()

    response = client.get("/rbac/probe/company-write", headers=auth_header_for(user))

    assert response.status_code == 403
    assert response.get_json()["message"] == "missing_permission"


def test_super_admin_can_access_without_tenant_role(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id, email="super@example.com")
    seed_rbac()

    super_admin = Role.query.filter_by(name="Super Admin", scope="platform", client_id=None).one()
    UserRoleRepository(db_session).assign_role(user.id, super_admin.id)
    db_session.commit()

    response = client.get("/rbac/probe/company-write", headers=auth_header_for(user))

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}
