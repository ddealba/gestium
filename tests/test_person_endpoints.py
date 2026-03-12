from datetime import date
import pytest

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.case import Case
from app.models.client import Client
from app.models.company import Company
from app.models.document import Document
from app.models.employee import Employee
from app.models.person import Person
from app.models.person_company_relation import PersonCompanyRelation
from app.models.person_request import PersonRequest
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


def create_company(db_session, client_id: str, name: str = "Company") -> Company:
    company = Company(client_id=client_id, name=name, tax_id=f"TAX-{name}", status="active")
    db_session.add(company)
    db_session.commit()
    return company


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


def test_upsert_person_portal_user(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "admin@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")
    person = create_person(db_session, tenant.id, "Ada", "DOC-PORTAL", "ada@example.com")

    response = client.post(
        f"/persons/{person.id}/portal-user",
        headers=auth_header_for(user),
        json={"email": "portal.ada@example.com", "password": "Password123"},
    )

    assert response.status_code == 200
    payload = response.get_json()["portal_user"]
    assert payload["user_type"] == "portal"
    assert payload["person_id"] == person.id
    assert payload["status"] == "active"

    user_row = User.query.filter_by(client_id=tenant.id, email="portal.ada@example.com").one()
    assert user_row.person_id == person.id
    assert user_row.user_type == "portal"


def test_upsert_person_portal_user_conflict(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "admin@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")
    person_a = create_person(db_session, tenant.id, "Ada", "DOC-A")
    person_b = create_person(db_session, tenant.id, "Grace", "DOC-B")

    db_session.add(
        User(
            client_id=tenant.id,
            email="portal@acme.com",
            status="active",
            user_type="portal",
            person_id=person_a.id,
            password_hash="x",
        )
    )
    db_session.commit()

    response = client.post(
        f"/persons/{person_b.id}/portal-user",
        headers=auth_header_for(user),
        json={"email": "portal@acme.com", "password": "Password123"},
    )

    assert response.status_code == 409
    assert response.get_json()["message"] == "email_already_in_use"


def test_person_overview_with_complete_data(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "ops@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")

    person = create_person(db_session, tenant.id, "Ada", "DOC-360", "ada@example.com")
    person.phone = "+34123123123"
    person.address_line1 = "Calle Mayor 1"
    person.city = "Madrid"
    person.postal_code = "28001"
    person.country = "ES"
    person.document_type = "dni"
    person.status = "active"

    company = create_company(db_session, tenant.id, "Acme Corp")
    relation = PersonCompanyRelation(
        client_id=tenant.id,
        person_id=person.id,
        company_id=company.id,
        relation_type="owner",
        status="active",
        start_date=date(2024, 1, 1),
    )
    employee = Employee(
        client_id=tenant.id,
        company_id=company.id,
        person_id=person.id,
        full_name="Ada Tester",
        status="active",
        start_date=date(2024, 1, 10),
    )
    case = Case(
        client_id=tenant.id,
        company_id=company.id,
        person_id=person.id,
        type="onboarding",
        title="Expediente onboarding",
        status="open",
    )
    db_session.add_all([relation, employee, case])
    db_session.flush()

    document = Document(
        client_id=tenant.id,
        company_id=company.id,
        person_id=person.id,
        employee_id=employee.id,
        case_id=case.id,
        original_filename="dni.pdf",
        storage_path="/tmp/dni.pdf",
        status="pending",
        doc_type="dni",
    )
    request = PersonRequest(
        client_id=tenant.id,
        person_id=person.id,
        request_type="upload_document",
        title="Subir DNI",
        status="pending",
        resolution_type="document_upload",
    )
    portal_user = User(
        client_id=tenant.id,
        person_id=person.id,
        email="portal.ada@example.com",
        status="active",
        user_type="portal",
    )
    db_session.add_all([document, request, portal_user])
    db_session.add(AuditLog(client_id=tenant.id, action="person.updated", entity_type="person", entity_id=person.id))
    db_session.commit()

    response = client.get(f"/persons/{person.id}/overview", headers=auth_header_for(user))
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["person"]["id"] == person.id
    assert payload["completeness"]["completion_pct"] == 100
    assert len(payload["companies"]) == 1
    assert payload["employee"]["id"] == employee.id
    assert len(payload["cases"]) == 1
    assert len(payload["documents"]) == 1
    assert payload["documents"][0]["contexts"] == ["personal", "laboral", "empresa", "expediente"]
    assert len(payload["requests"]) == 1
    assert payload["portal_access"]["status"] == "active"
    assert len(payload["audit"]) >= 1


def test_person_overview_without_relations(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "ops@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Operativo")
    person = create_person(db_session, tenant.id, "Solo", "DOC-SOLO")

    response = client.get(f"/persons/{person.id}/overview", headers=auth_header_for(user))
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["companies"] == []
    assert payload["employee"] is None
    assert payload["cases"] == []
    assert payload["documents"] == []
    assert payload["requests"] == []
    assert payload["portal_access"] is None


def test_person_overview_tenant_isolation(client, db_session):
    tenant_a = create_client(db_session, "Acme")
    tenant_b = create_client(db_session, "Beta")
    user_a = create_user(db_session, tenant_a.id, "a@acme.com")
    seed_rbac()
    assign_role(db_session, user_a, "Operativo")
    person_b = create_person(db_session, tenant_b.id, "Private", "B-2")

    response = client.get(f"/persons/{person_b.id}/overview", headers=auth_header_for(user_a))
    assert response.status_code == 404


def test_person_overview_without_permission_returns_403(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "noperms@acme.com")
    person = create_person(db_session, tenant.id, "Ada", "DOC-403")

    response = client.get(f"/persons/{person.id}/overview", headers=auth_header_for(user))
    assert response.status_code == 403


def test_person_completeness_and_generate_requests(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "admin.requests@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")

    person = create_person(db_session, tenant.id, "Ada", "DOC-GEN", "ada@example.com")

    completeness_response = client.get(f"/persons/{person.id}/completeness", headers=auth_header_for(user))
    assert completeness_response.status_code == 200
    completeness = completeness_response.get_json()["completeness"]
    assert completeness["status"] in {"draft", "pending_info"}
    assert "phone" in completeness["missing_fields"]
    assert "dni" in completeness["missing_documents"]

    generate_response = client.post(f"/persons/{person.id}/generate-requests", headers=auth_header_for(user))
    assert generate_response.status_code == 200
    created = generate_response.get_json()["created"]
    assert created >= 1

    second_response = client.post(f"/persons/{person.id}/generate-requests", headers=auth_header_for(user))
    assert second_response.status_code == 200
    assert second_response.get_json()["created"] == 0


def test_person_status_recalculated_to_active(client, db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id, "admin.active@acme.com")
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")

    create_response = client.post(
        "/persons",
        headers=auth_header_for(user),
        json={
            "first_name": "Lina",
            "last_name": "Active",
            "document_type": "dni",
            "document_number": "DNI-ACT-1",
            "email": "lina@example.com",
            "phone": "+340000000",
            "address_line1": "Street 1",
            "city": "Madrid",
            "postal_code": "28001",
            "country": "ES",
        },
    )
    assert create_response.status_code == 201
    person_id = create_response.get_json()["person"]["id"]

    portal_response = client.post(
        f"/persons/{person_id}/portal-user",
        headers=auth_header_for(user),
        json={"email": "lina.portal@example.com", "password": "Password123"},
    )
    assert portal_response.status_code == 200

    db_session.add(Document(client_id=tenant.id, person_id=person_id, original_filename="dni.pdf", storage_path="/tmp/dni.pdf", doc_type="dni", status="processed"))
    from app.modules.person.person_completeness_service import PersonCompletenessService
    person_row = db_session.query(Person).filter_by(id=person_id, client_id=tenant.id).one()
    PersonCompletenessService().recalculate_person_status(person_row, actor_user_id=user.id)
    db_session.commit()

    overview = client.get(f"/persons/{person_id}/overview", headers=auth_header_for(user)).get_json()
    assert overview["person"]["status"] == "active"
    assert overview["completeness"]["status"] == "active"

def test_person_completeness_tenant_isolation(client, db_session):
    tenant_a = create_client(db_session, "Iso A")
    tenant_b = create_client(db_session, "Iso B")
    user_a = create_user(db_session, tenant_a.id, "iso.a@acme.com")
    seed_rbac()
    assign_role(db_session, user_a, "Operativo")

    person_b = create_person(db_session, tenant_b.id, "Other", "ISO-OTHER")
    response = client.get(f"/persons/{person_b.id}/completeness", headers=auth_header_for(user_a))
    assert response.status_code == 404
