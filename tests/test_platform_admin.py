import uuid

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.client import Client
from app.models.company import Company
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


def test_super_admin_can_list_and_create_tenant(app, client):
    with app.app_context():
        db.create_all()
        tenant_a = _create_client("Tenant A")
        seed_rbac()

        super_admin_user = _create_user(tenant_a.id, "super@example.com")
        super_admin_role = Role.query.filter_by(name="Super Admin", scope="platform", client_id=None).one()
        UserRoleRepository(db.session).assign_role(super_admin_user.id, super_admin_role.id)
        db.session.commit()

        list_response = client.get("/platform/tenants", headers=_auth_header(super_admin_user))
        assert list_response.status_code == 200
        payload = list_response.get_json()
        assert payload["total"] >= 1
        assert payload["items"][0]["metrics"]["companies"] is not None
        assert payload["items"][0]["metrics"]["users"] is not None

        create_response = client.post(
            "/platform/tenants",
            headers=_auth_header(super_admin_user),
            json={"name": "Tenant Nuevo", "plan": "pro", "admin_email": "admin.nuevo@example.com"},
        )
        assert create_response.status_code == 201
        created = create_response.get_json()["tenant"]
        assert created["name"] == "Tenant Nuevo"
        assert created["status"] == "active"

        db.drop_all()


def test_tenant_admin_gets_403_on_platform_endpoints(app, client):
    with app.app_context():
        db.create_all()
        tenant_a = _create_client("Tenant A")
        seed_rbac()

        tenant_admin_user = _create_user(tenant_a.id, "tenant.admin@example.com")
        tenant_admin_role = Role.query.filter_by(name="Admin Cliente", scope="tenant", client_id=tenant_a.id).one()
        UserRoleRepository(db.session).assign_role(tenant_admin_user.id, tenant_admin_role.id)
        db.session.commit()

        response = client.get("/platform/tenants", headers=_auth_header(tenant_admin_user))
        assert response.status_code == 403
        assert response.get_json()["message"] == "missing_permission"

        db.drop_all()


def test_created_tenant_persists_and_appears_with_metrics(app, client):
    with app.app_context():
        db.create_all()
        root_tenant = _create_client("Root Tenant")
        seed_rbac()

        super_admin_user = _create_user(root_tenant.id, "super2@example.com")
        super_admin_role = Role.query.filter_by(name="Super Admin", scope="platform", client_id=None).one()
        UserRoleRepository(db.session).assign_role(super_admin_user.id, super_admin_role.id)
        db.session.commit()

        create_response = client.post(
            "/platform/tenants",
            headers=_auth_header(super_admin_user),
            json={"name": "Tenant Métricas", "plan": "basic", "status": "active"},
        )
        assert create_response.status_code == 201
        tenant_id = create_response.get_json()["tenant"]["id"]

        company = Company(client_id=tenant_id, name="Empresa 1", tax_id="TX-001", status="active")
        db.session.add(company)
        user = User(client_id=tenant_id, email="nuevo@tenant.com", status="active")
        db.session.add(user)
        db.session.commit()

        list_response = client.get("/platform/tenants?q=Métricas", headers=_auth_header(super_admin_user))
        assert list_response.status_code == 200
        listed_items = list_response.get_json()["items"]
        assert len(listed_items) == 1
        assert listed_items[0]["id"] == tenant_id
        assert listed_items[0]["metrics"]["companies"] == 1
        assert listed_items[0]["metrics"]["users"] == 1

        patch_response = client.patch(
            f"/platform/tenants/{tenant_id}",
            headers=_auth_header(super_admin_user),
            json={"name": "Tenant Métricas Updated", "plan": "pro", "status": "suspended"},
        )
        assert patch_response.status_code == 200
        updated = patch_response.get_json()["tenant"]
        assert updated["name"] == "Tenant Métricas Updated"
        assert updated["status"] == "suspended"

        db.drop_all()
