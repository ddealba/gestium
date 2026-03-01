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
    assert {"dashboard", "companies", "employees", "cases", "documents", "admin"}.issubset(page_ids)

    admin_group = next(item for item in nav_items if item["page_id"] == "admin")
    admin_children = {child["page_id"] for child in admin_group["children"]}
    assert {"admin_users", "admin_access"}.issubset(admin_children)


def test_new_tenant_level_routes_render(client):
    response = client.get('/app/employees')
    assert response.status_code == 200

    response = client.get('/app/cases')
    assert response.status_code == 200

    response = client.get('/app/documents')
    assert response.status_code == 200
