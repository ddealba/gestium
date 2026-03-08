import pytest

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.client import Client
from app.models.company import Company
from app.models.person import Person
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


def create_person(db_session, client_id: str, first_name: str, document_number: str) -> Person:
    person = Person(
        client_id=client_id,
        first_name=first_name,
        last_name="Tester",
        document_number=document_number,
        status="active",
    )
    db_session.add(person)
    db_session.commit()
    return person


def create_company(db_session, client_id: str, name: str, tax_id: str) -> Company:
    company = Company(client_id=client_id, name=name, tax_id=tax_id, status="active")
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


def _create_relation(client, user, person_id: str, company_id: str):
    return client.post(
        f"/persons/{person_id}/companies",
        headers=auth_header_for(user),
        json={
            "company_id": company_id,
            "relation_type": "owner",
            "start_date": "2026-03-01",
            "notes": "Representante principal",
        },
    )


def test_create_valid_relation(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "admin@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")
    person = create_person(db_session, tenant.id, "Ada", "DOC-1")
    company = create_company(db_session, tenant.id, "ACME SA", "A0001")

    response = _create_relation(client, user, person.id, company.id)

    assert response.status_code == 201
    payload = response.get_json()["relation"]
    assert payload["relation_type"] == "owner"
    assert payload["status"] == "active"


def test_prevent_duplicate_active_relation(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "admin@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")
    person = create_person(db_session, tenant.id, "Ada", "DOC-1")
    company = create_company(db_session, tenant.id, "ACME SA", "A0001")

    first = _create_relation(client, user, person.id, company.id)
    second = _create_relation(client, user, person.id, company.id)

    assert first.status_code == 201
    assert second.status_code == 400
    assert second.get_json()["message"] == "duplicate_active_relation"


def test_list_relations_by_person(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "admin@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")
    person = create_person(db_session, tenant.id, "Ada", "DOC-1")
    company = create_company(db_session, tenant.id, "ACME SA", "A0001")
    _create_relation(client, user, person.id, company.id)

    response = client.get(f"/persons/{person.id}/companies", headers=auth_header_for(user))

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["company_name"] == "ACME SA"


def test_list_relations_by_company(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "admin@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")
    person = create_person(db_session, tenant.id, "Ada", "DOC-1")
    company = create_company(db_session, tenant.id, "ACME SA", "A0001")
    _create_relation(client, user, person.id, company.id)

    response = client.get(f"/companies/{company.id}/persons", headers=auth_header_for(user))

    assert response.status_code == 200
    items = response.get_json()["items"]
    assert len(items) == 1
    assert items[0]["full_name"] == "Ada Tester"


def test_deactivate_relation(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "admin@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")
    person = create_person(db_session, tenant.id, "Ada", "DOC-1")
    company = create_company(db_session, tenant.id, "ACME SA", "A0001")
    create_response = _create_relation(client, user, person.id, company.id)
    relation_id = create_response.get_json()["relation"]["id"]

    deactivate_response = client.post(
        f"/person-company-relations/{relation_id}/deactivate",
        headers=auth_header_for(user),
    )

    assert deactivate_response.status_code == 200
    assert deactivate_response.get_json()["relation"]["status"] == "inactive"


def test_tenant_isolation(client, db_session):
    tenant_a = create_client(db_session, "Acme")
    tenant_b = create_client(db_session, "Beta")
    user_a = create_user(db_session, tenant_a.id, "a@acme.com")
    user_b = create_user(db_session, tenant_b.id, "b@beta.com")
    seed_rbac()
    assign_role(db_session, user_a, "Admin Cliente")
    assign_role(db_session, user_b, "Admin Cliente")

    person_b = create_person(db_session, tenant_b.id, "Private", "B-1")
    company_b = create_company(db_session, tenant_b.id, "Beta SA", "B0001")
    _create_relation(client, user_b, person_b.id, company_b.id)

    response = client.get(f"/persons/{person_b.id}/companies", headers=auth_header_for(user_a))

    assert response.status_code == 404
