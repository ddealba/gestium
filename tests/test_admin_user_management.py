from werkzeug.security import generate_password_hash

import pytest

from app.extensions import db
from app.models.client import Client
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User


@pytest.fixture()
def db_session(app):
    app.config["ALLOW_X_CLIENT_ID_HEADER"] = False
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


def create_user(db_session, client_id: str, email: str, password: str, status: str = "active") -> User:
    user = User(
        client_id=client_id,
        email=email,
        status=status,
        password_hash=generate_password_hash(password),
    )
    db_session.add(user)
    db_session.commit()
    return user


def create_role_with_permissions(db_session, client_id: str, role_name: str, permission_codes: list[str]) -> Role:
    permissions = []
    for code in permission_codes:
        permission = db_session.query(Permission).filter_by(code=code).one_or_none()
        if permission is None:
            permission = Permission(code=code, description=code)
            db_session.add(permission)
            db_session.flush()
        permissions.append(permission)

    role = Role(name=role_name, scope="tenant", client_id=client_id, permissions=permissions)
    db_session.add(role)
    db_session.commit()
    return role


def login_user(client, email: str, password: str, client_id: str) -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password, "client_id": client_id},
    )
    assert response.status_code == 200
    return response.get_json()["access_token"]


def test_admin_can_list_invite_and_disable_users(client, db_session):
    tenant = create_client(db_session, "Tenant A")
    admin = create_user(db_session, tenant.id, "admin@tenant-a.com", "supersecret")

    admin_role = create_role_with_permissions(
        db_session,
        tenant.id,
        "Tenant Admin",
        ["tenant.user.read", "tenant.user.invite", "tenant.user.manage", "tenant.role.read"],
    )
    admin.roles.append(admin_role)
    db_session.commit()

    token = login_user(client, admin.email, "supersecret", tenant.id)
    headers = {"Authorization": f"Bearer {token}"}

    list_response = client.get("/admin/users", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.get_json()["items"]) == 1

    invite_response = client.post(
        "/admin/users/invite",
        json={"email": "new.user@tenant-a.com"},
        headers=headers,
    )
    assert invite_response.status_code == 201
    invite_payload = invite_response.get_json()
    assert invite_payload["status"] == "invited"
    invited_user = db_session.query(User).filter_by(client_id=tenant.id, email="new.user@tenant-a.com").one()

    disable_response = client.post(f"/admin/users/{invited_user.id}/disable", headers=headers)
    assert disable_response.status_code == 200
    assert disable_response.get_json()["status"] == "disabled"


def test_normal_user_cannot_manage_users(client, db_session):
    tenant = create_client(db_session, "Tenant A")
    user = create_user(db_session, tenant.id, "user@tenant-a.com", "supersecret")
    token = login_user(client, user.email, "supersecret", tenant.id)

    response = client.get("/admin/users", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    assert response.get_json()["message"] == "missing_permission"


def test_normal_user_cannot_invite_users(client, db_session):
    tenant = create_client(db_session, "Tenant A")
    user = create_user(db_session, tenant.id, "user@tenant-a.com", "supersecret")
    token = login_user(client, user.email, "supersecret", tenant.id)

    response = client.post(
        "/admin/users/invite",
        json={"email": "new.user@tenant-a.com"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.get_json()["message"] == "missing_permission"


def test_cross_tenant_returns_404(client, db_session):
    tenant_a = create_client(db_session, "Tenant A")
    tenant_b = create_client(db_session, "Tenant B")

    admin_a = create_user(db_session, tenant_a.id, "admin@tenant-a.com", "supersecret")
    target_b = create_user(db_session, tenant_b.id, "user@tenant-b.com", "supersecret")

    admin_role = create_role_with_permissions(
        db_session,
        tenant_a.id,
        "Tenant Admin",
        ["tenant.user.manage", "tenant.user.read"],
    )
    admin_a.roles.append(admin_role)
    db_session.commit()

    token = login_user(client, admin_a.email, "supersecret", tenant_a.id)

    response = client.post(
        f"/admin/users/{target_b.id}/disable",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 404
    assert response.get_json()["message"] == "user_not_found"
