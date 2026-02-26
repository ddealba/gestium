import uuid

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.client import Client
from app.models.role import Role
from app.models.user import User
from app.repositories.user_role_repository import UserRoleRepository


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.client_id)
    return {"Authorization": f"Bearer {token}"}


def _create_client(name: str, status: str = "active", plan: str | None = "basic") -> Client:
    client = Client(id=str(uuid.uuid4()), name=name, status=status, plan=plan)
    db.session.add(client)
    db.session.commit()
    return client


def _create_user(client_id: str, email: str) -> User:
    user = User(client_id=client_id, email=email, status="active")
    db.session.add(user)
    db.session.commit()
    return user


def test_tenant_required_missing_client_id(app):
    client = app.test_client()

    response = client.get("/health/tenant")

    assert response.status_code == 400
    assert response.get_json() == {
        "error": {"code": "tenant_context_required", "message": "Selecciona un tenant"}
    }


def test_tenant_header_sets_client_id(app):
    app.config["ALLOW_X_CLIENT_ID_HEADER"] = True
    client = app.test_client()
    client_id = str(uuid.uuid4())

    response = client.get("/health/tenant", headers={"X-Client-Id": client_id})

    assert response.status_code == 200
    assert response.get_json() == {"client_id": client_id}


def test_invalid_client_id_returns_bad_request(app):
    app.config["ALLOW_X_CLIENT_ID_HEADER"] = True
    client = app.test_client()

    response = client.get("/health/tenant", headers={"X-Client-Id": "not-a-uuid"})

    assert response.status_code == 400
    assert response.get_json()["message"] == "Invalid client_id format."


def test_super_admin_requires_tenant_header_for_tenant_scoped_endpoints(app, client):
    with app.app_context():
        db.create_all()
        tenant_a = _create_client(f"Tenant A {uuid.uuid4()}")
        seed_rbac()

        super_admin_user = _create_user(tenant_a.id, "super.noctx@example.com")
        super_admin_role = Role.query.filter_by(name="Super Admin", scope="platform", client_id=None).one()
        UserRoleRepository(db.session).assign_role(super_admin_user.id, super_admin_role.id)
        db.session.commit()

        response = client.get("/companies", headers=_auth_header(super_admin_user))

        assert response.status_code == 400
        assert response.get_json() == {
            "error": {"code": "tenant_context_required", "message": "Selecciona un tenant"}
        }



def test_super_admin_can_use_valid_admin_tenant_header(app, client):
    with app.app_context():
        db.create_all()
        tenant_a = _create_client(f"Tenant A {uuid.uuid4()}")
        tenant_b = _create_client(f"Tenant B {uuid.uuid4()}")
        seed_rbac()

        super_admin_user = _create_user(tenant_a.id, "super.ctx@example.com")
        super_admin_role = Role.query.filter_by(name="Super Admin", scope="platform", client_id=None).one()
        UserRoleRepository(db.session).assign_role(super_admin_user.id, super_admin_role.id)
        db.session.commit()

        response = client.get(
            "/companies",
            headers={**_auth_header(super_admin_user), "X-Admin-Tenant": tenant_b.id},
        )

        assert response.status_code == 200



def test_normal_user_cannot_override_tenant_with_admin_header(app, client):
    with app.app_context():
        db.create_all()
        tenant_a = _create_client(f"Tenant A {uuid.uuid4()}")
        tenant_b = _create_client(f"Tenant B {uuid.uuid4()}")
        seed_rbac()

        tenant_admin_user = _create_user(tenant_a.id, "tenant.admin@example.com")
        tenant_admin_role = Role.query.filter_by(name="Admin Cliente", scope="tenant", client_id=tenant_a.id).one()
        UserRoleRepository(db.session).assign_role(tenant_admin_user.id, tenant_admin_role.id)
        db.session.commit()

        response = client.get(
            "/companies",
            headers={**_auth_header(tenant_admin_user), "X-Admin-Tenant": tenant_b.id},
        )

        assert response.status_code == 200
        assert response.get_json()["total"] == 0



def test_super_admin_with_nonexistent_tenant_header_fails(app, client):
    with app.app_context():
        db.create_all()
        tenant_a = _create_client(f"Tenant A {uuid.uuid4()}")
        seed_rbac()

        super_admin_user = _create_user(tenant_a.id, "super.notfound@example.com")
        super_admin_role = Role.query.filter_by(name="Super Admin", scope="platform", client_id=None).one()
        UserRoleRepository(db.session).assign_role(super_admin_user.id, super_admin_role.id)
        db.session.commit()

        response = client.get(
            "/companies",
            headers={**_auth_header(super_admin_user), "X-Admin-Tenant": str(uuid.uuid4())},
        )

        assert response.status_code == 404
        assert response.get_json() == {
            "error": {"code": "tenant_not_found", "message": "Tenant no encontrado"}
        }

