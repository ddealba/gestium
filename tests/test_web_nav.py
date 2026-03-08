from app.common.jwt import create_access_token
from app.extensions import db
from app.models.client import Client
from app.models.user import User
from app.modules.web.routes import _build_nav_items


def test_build_nav_items_contains_expected_sections():
    nav_items = _build_nav_items()

    dashboard = next(item for item in nav_items if item["page_id"] == "dashboard")
    assert dashboard["scope"] == "tenant"

    platform_group = next(item for item in nav_items if item["page_id"] == "platform")
    assert platform_group["label"] == "Plataforma"

    tenant_entry = next(child for child in platform_group["children"] if child["page_id"] == "platform_tenants")
    assert tenant_entry["label"] == "Gestorías (Tenants)"


def test_tenant_level_menu_entries_present():
    nav_items = _build_nav_items()

    page_ids = {item["page_id"] for item in nav_items}
    assert {"dashboard", "companies", "employees", "persons", "cases", "documents", "admin"}.issubset(page_ids)

    admin_group = next(item for item in nav_items if item["page_id"] == "admin")
    admin_children = {child["page_id"] for child in admin_group["children"]}
    assert {"admin_users", "admin_access"}.issubset(admin_children)


def test_new_tenant_level_routes_render(client, app):
    with app.app_context():
        db.create_all()
        tenant = Client(name="Tenant Web", status="active")
        db.session.add(tenant)
        db.session.flush()
        user = User(
            client_id=tenant.id,
            email="web@example.com",
            status="active",
            user_type="internal",
            password_hash="x",
        )
        db.session.add(user)
        db.session.commit()

        token = create_access_token(user.id, tenant.id)
        headers = {"Authorization": f"Bearer {token}"}

        response = client.get('/app/employees', headers=headers)
        assert response.status_code == 200

        response = client.get('/app/persons', headers=headers)
        assert response.status_code == 200

        response = client.get('/app/cases', headers=headers)
        assert response.status_code == 200

        response = client.get('/app/documents', headers=headers)
        assert response.status_code == 200

        db.drop_all()
