import pytest

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.client import Client
from app.models.person import Person
from app.models.role import Role
from app.models.user import User
from app.modules.audit.models import AuditLog
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


def auth_header_for(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.client_id)
    return {"Authorization": f"Bearer {token}"}


def assign_role(db_session, user: User, role_name: str) -> None:
    role = Role.query.filter_by(name=role_name, scope="tenant", client_id=user.client_id).one()
    UserRoleRepository(db_session).assign_role(user.id, role.id)
    db_session.commit()


def create_person(db_session, client_id: str, first_name: str, document_number: str, email: str | None = None) -> Person:
    person = Person(
        client_id=client_id,
        first_name=first_name,
        last_name="Tester",
        document_number=document_number,
        email=email,
        status="draft",
    )
    db_session.add(person)
    db_session.commit()
    return person


def test_create_person(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "admin@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")

    response = client.post(
        "/persons",
        headers=auth_header_for(user),
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "document_number": "DNI-123",
            "email": "ada@example.com",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["person"]
    assert payload["status"] == "draft"
    assert payload["first_name"] == "Ada"

    audit_rows = AuditLog.query.filter_by(client_id=tenant.id, entity_type="person", action="person.created").all()
    assert len(audit_rows) == 1


def test_list_and_search_persons(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "user@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Operativo")

    create_person(db_session, tenant.id, "Ada", "DOC-1", "ada@example.com")
    create_person(db_session, tenant.id, "Grace", "DOC-2", "grace@example.com")

    response = client.get("/persons", headers=auth_header_for(user))
    assert response.status_code == 200
    assert response.get_json()["total"] == 2

    response = client.get("/persons?search=Grace", headers=auth_header_for(user))
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 1
    assert payload["items"][0]["first_name"] == "Grace"


def test_duplicate_document_validation(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "admin@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")

    create_person(db_session, tenant.id, "Ada", "DUP-1")

    response = client.post(
        "/persons",
        headers=auth_header_for(user),
        json={
            "first_name": "Grace",
            "last_name": "Hopper",
            "document_number": "DUP-1",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["message"] == "duplicate_document_number"


def test_tenant_isolation_for_person_detail(client, db_session):
    tenant_a = create_client(db_session, "Acme")
    tenant_b = create_client(db_session, "Beta")

    user_a = create_user(db_session, tenant_a.id, "a@acme.com")
    user_b = create_user(db_session, tenant_b.id, "b@beta.com")
    seed_rbac()
    assign_role(db_session, user_a, "Operativo")
    assign_role(db_session, user_b, "Operativo")

    person_b = create_person(db_session, tenant_b.id, "Private", "B-1")

    response = client.get(f"/persons/{person_b.id}", headers=auth_header_for(user_a))
    assert response.status_code == 404
