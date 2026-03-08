from datetime import date

import pytest

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.client import Client
from app.models.company import Company
from app.models.employee import Employee
from app.models.person import Person
from app.models.person_company_relation import PersonCompanyRelation
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


def create_client(db_session, name: str = "Acme") -> Client:
    client = Client(name=name)
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


def create_person(
    db_session,
    client_id: str,
    first_name: str = "Ada",
    last_name: str = "Lovelace",
    document_number: str = "DOC-1",
) -> Person:
    person = Person(
        client_id=client_id,
        first_name=first_name,
        last_name=last_name,
        document_number=document_number,
        status="active",
    )
    db_session.add(person)
    db_session.commit()
    return person


def create_employee(
    db_session,
    client_id: str,
    company_id: str,
    full_name: str = "Ada Lovelace",
    status: str = "active",
    start_date_value: date = date(2024, 1, 1),
    end_date_value: date | None = None,
    person_id: str | None = None,
) -> Employee:
    employee = Employee(
        client_id=client_id,
        company_id=company_id,
        person_id=person_id,
        full_name=full_name,
        status=status,
        start_date=start_date_value,
        end_date=end_date_value,
    )
    db_session.add(employee)
    db_session.commit()
    return employee


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


def test_viewer_can_list_but_not_create_employees(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()

    assign_role(db_session, user, "Operativo")
    company = create_company(db_session, tenant.id, "Alpha", "A-123")
    assign_access(db_session, user, company, "viewer")
    create_employee(db_session, tenant.id, company.id)

    response = client.get(f"/companies/{company.id}/employees", headers=auth_header_for(user))

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["items"]) == 1
    assert payload["total"] == 1

    response = client.post(
        f"/companies/{company.id}/employees",
        headers=auth_header_for(user),
        json={
            "full_name": "Grace Hopper",
            "start_date": "2024-02-01",
        },
    )

    assert response.status_code == 403


def test_operator_can_create_and_update_employees(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()

    assign_role(db_session, user, "Admin Cliente")
    company = create_company(db_session, tenant.id, "Alpha", "A-123")
    assign_access(db_session, user, company, "operator")

    response = client.post(
        f"/companies/{company.id}/employees",
        headers=auth_header_for(user),
        json={
            "full_name": "Grace Hopper",
            "employee_ref": "EMP-01",
            "start_date": "2024-02-01",
        },
    )

    assert response.status_code == 201
    employee_id = response.get_json()["employee"]["id"]

    response = client.patch(
        f"/companies/{company.id}/employees/{employee_id}",
        headers=auth_header_for(user),
        json={"full_name": "Grace B. Hopper", "employee_ref": "EMP-02"},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["employee"]["full_name"] == "Grace B. Hopper"
    assert payload["employee"]["employee_ref"] == "EMP-02"


def test_create_employee_with_person_auto_creates_relation(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")
    company = create_company(db_session, tenant.id, "Alpha", "A-123")
    person = create_person(db_session, tenant.id, document_number="DOC-EMP")
    assign_access(db_session, user, company, "operator")

    response = client.post(
        f"/companies/{company.id}/employees",
        headers=auth_header_for(user),
        json={
            "person_id": person.id,
            "status": "active",
            "hire_date": "2026-03-01",
        },
    )

    assert response.status_code == 201
    payload = response.get_json()["employee"]
    assert payload["person_id"] == person.id
    assert payload["legacy_employee"] is False

    relation = PersonCompanyRelation.query.filter_by(
        client_id=tenant.id,
        person_id=person.id,
        company_id=company.id,
        relation_type="employee",
        status="active",
    ).one_or_none()
    assert relation is not None


def test_list_employees_includes_person_data(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()
    assign_role(db_session, user, "Operativo")
    company = create_company(db_session, tenant.id, "Alpha", "A-123")
    person = create_person(db_session, tenant.id, first_name="Grace", last_name="Hopper", document_number="DOC-2")
    assign_access(db_session, user, company, "viewer")
    create_employee(db_session, tenant.id, company.id, full_name="Legacy Name", person_id=person.id)

    response = client.get(f"/companies/{company.id}/employees", headers=auth_header_for(user))

    assert response.status_code == 200
    item = response.get_json()["items"][0]
    assert item["person_id"] == person.id
    assert item["person_full_name"] == "Grace Hopper"
    assert item["person_document_number"] == "DOC-2"


def test_legacy_create_without_person_still_works(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")
    company = create_company(db_session, tenant.id, "Alpha", "A-123")
    assign_access(db_session, user, company, "operator")

    response = client.post(
        f"/companies/{company.id}/employees",
        headers=auth_header_for(user),
        json={"full_name": "Legacy Employee", "start_date": "2024-02-01"},
    )

    assert response.status_code == 201
    payload = response.get_json()["employee"]
    assert payload["person_id"] is None
    assert payload["legacy_employee"] is True


def test_reject_person_from_other_tenant(client, db_session):
    tenant_a = create_client(db_session)
    tenant_b = create_client(db_session, name="Globex")
    user = create_user(db_session, tenant_a.id)
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")

    company = create_company(db_session, tenant_a.id, "Alpha", "A-123")
    person_other = create_person(db_session, tenant_b.id, document_number="DOC-OTHER")
    assign_access(db_session, user, company, "operator")

    response = client.post(
        f"/companies/{company.id}/employees",
        headers=auth_header_for(user),
        json={"person_id": person_other.id, "start_date": "2024-02-01"},
    )

    assert response.status_code == 404


def test_reject_company_from_other_tenant(client, db_session):
    tenant_a = create_client(db_session)
    tenant_b = create_client(db_session, name="Globex")
    user = create_user(db_session, tenant_a.id)
    seed_rbac()
    assign_role(db_session, user, "Admin Cliente")

    company_other = create_company(db_session, tenant_b.id, "Other", "O-123")

    response = client.post(
        f"/companies/{company_other.id}/employees",
        headers=auth_header_for(user),
        json={"full_name": "Nope", "start_date": "2024-02-01"},
    )

    assert response.status_code == 404


def test_terminate_validation_requires_end_date(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()

    assign_role(db_session, user, "Admin Cliente")
    company = create_company(db_session, tenant.id, "Alpha", "A-123")
    assign_access(db_session, user, company, "operator")

    response = client.post(
        f"/companies/{company.id}/employees",
        headers=auth_header_for(user),
        json={
            "full_name": "Grace Hopper",
            "status": "terminated",
            "start_date": "2024-02-01",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["message"] == "end_date_required"


def test_terminate_validation_rejects_end_date_before_start(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()

    assign_role(db_session, user, "Admin Cliente")
    company = create_company(db_session, tenant.id, "Alpha", "A-123")
    assign_access(db_session, user, company, "operator")
    employee = create_employee(db_session, tenant.id, company.id)

    response = client.patch(
        f"/companies/{company.id}/employees/{employee.id}",
        headers=auth_header_for(user),
        json={"status": "terminated", "end_date": "2023-12-31"},
    )

    assert response.status_code == 400
    assert response.get_json()["message"] == "end_date_before_start_date"


def test_cross_company_employee_access_is_denied(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    seed_rbac()

    assign_role(db_session, user, "Operativo")
    company_a = create_company(db_session, tenant.id, "Alpha", "A-123")
    company_b = create_company(db_session, tenant.id, "Beta", "B-456")
    assign_access(db_session, user, company_a, "viewer")
    employee_b = create_employee(db_session, tenant.id, company_b.id, full_name="Ada Lovelace")

    response = client.get(
        f"/companies/{company_a.id}/employees/{employee_b.id}",
        headers=auth_header_for(user),
    )

    assert response.status_code == 404
