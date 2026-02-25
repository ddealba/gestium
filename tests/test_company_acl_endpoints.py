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
    repository = UserCompanyAccessRepository(db_session)
    repository.upsert_access(user.id, company.id, user.client_id, level)
    db_session.commit()


def test_list_companies_filters_by_acl(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()

    assign_role(db_session, user, "Operativo")
    company_a = create_company(db_session, tenant.id, "Alpha", "A-123")
    create_company(db_session, tenant.id, "Beta", "B-456")
    assign_access(db_session, user, company_a, "viewer")

    response = client.get("/companies", headers=auth_header_for(user))

    assert response.status_code == 200
    payload = response.get_json()
    assert [company["id"] for company in payload["items"]] == [company_a.id]
    assert payload["total"] == 1


def test_list_companies_without_acl_returns_empty(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()

    assign_role(db_session, user, "Operativo")
    create_company(db_session, tenant.id, "Alpha", "A-123")

    response = client.get("/companies", headers=auth_header_for(user))

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["items"] == []
    assert payload["total"] == 0


def test_get_company_out_of_scope_returns_404(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()

    assign_role(db_session, user, "Operativo")
    company_a = create_company(db_session, tenant.id, "Alpha", "A-123")
    company_b = create_company(db_session, tenant.id, "Beta", "B-456")
    assign_access(db_session, user, company_a, "viewer")

    response = client.get(f"/companies/{company_b.id}", headers=auth_header_for(user))

    assert response.status_code == 404


def test_patch_company_insufficient_access_returns_403(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()

    assign_role(db_session, user, "Admin Cliente")
    company_a = create_company(db_session, tenant.id, "Alpha", "A-123")
    assign_access(db_session, user, company_a, "viewer")

    response = client.patch(
        f"/companies/{company_a.id}",
        headers=auth_header_for(user),
        json={"name": "Alpha Updated"},
    )

    assert response.status_code == 403
    assert response.get_json()["message"] == "Insufficient access level."


def test_rbac_denies_even_with_acl(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()

    company_a = create_company(db_session, tenant.id, "Alpha", "A-123")
    assign_access(db_session, user, company_a, "viewer")

    response = client.get(f"/companies/{company_a.id}", headers=auth_header_for(user))

    assert response.status_code == 403
    assert response.get_json()["message"] == "missing_permission"


def test_create_company_assigns_admin_access(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()

    assign_role(db_session, user, "Admin Cliente")

    response = client.post(
        "/companies",
        headers=auth_header_for(user),
        json={"name": "Gamma", "tax_id": "c-789"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    company_id = payload["company"]["id"]

    access = UserCompanyAccessRepository(db_session).get_user_access(
        user.id,
        company_id,
        user.client_id,
    )

    assert access is not None
    assert access.access_level == "admin"
