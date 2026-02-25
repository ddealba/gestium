import uuid

import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.client import Client
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.modules.audit.models import AuditLog


@pytest.fixture()
def db_session(app):
    app.config["ALLOW_X_CLIENT_ID_HEADER"] = False
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
        db.drop_all()


def create_client(db_session, name: str) -> Client:
    client = Client(name=f"{name}-{uuid.uuid4()}")
    db_session.add(client)
    db_session.commit()
    return client


def create_user(db_session, client_id: str, email: str, password: str = "supersecret") -> User:
    user = User(
        client_id=client_id,
        email=email,
        status="active",
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


def test_invite_user_creates_audit_log(client, db_session):
    tenant = create_client(db_session, "Tenant A")
    admin = create_user(db_session, tenant.id, "admin@tenant-a.com")
    role = create_role_with_permissions(
        db_session,
        tenant.id,
        "Tenant Admin",
        ["tenant.user.invite", "tenant.user.read"],
    )
    admin.roles.append(role)
    db_session.commit()

    token = login_user(client, admin.email, "supersecret", tenant.id)
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/admin/users/invite", json={"email": "new.user@tenant-a.com"}, headers=headers)
    assert response.status_code == 201

    log = db_session.query(AuditLog).filter_by(client_id=tenant.id, action="invite_user").one_or_none()
    assert log is not None
    assert log.entity_type == "user"


def test_admin_audit_endpoint_filters_by_tenant(client, db_session):
    tenant_a = create_client(db_session, "Tenant A")
    tenant_b = create_client(db_session, "Tenant B")

    admin_a = create_user(db_session, tenant_a.id, "admin@tenant-a.com")
    role = create_role_with_permissions(
        db_session,
        tenant_a.id,
        "Tenant Admin",
        ["tenant.user.invite", "tenant.user.read"],
    )
    admin_a.roles.append(role)

    db_session.add(
        AuditLog(
            client_id=tenant_b.id,
            actor_user_id=None,
            action="invite_user",
            entity_type="user",
            entity_id="external",
            metadata_json={},
        )
    )
    db_session.commit()

    token = login_user(client, admin_a.email, "supersecret", tenant_a.id)
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/admin/users/invite", json={"email": "only.a@tenant-a.com"}, headers=headers)

    response = client.get("/admin/audit?entity_type=user", headers=headers)
    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) >= 1
    assert all(item["client_id"] == tenant_a.id for item in items)
