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


def test_cases_crud_and_events_flow(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    assignee = create_user(db_session, tenant.id, email="assignee@example.com")
    company = create_company(db_session, tenant.id, "Alpha", "A-123")
    seed_rbac()

    assign_role(db_session, user, "Admin Cliente")
    assign_access(db_session, user, company, "admin")

    create_response = client.post(
        f"/companies/{company.id}/cases",
        headers=auth_header_for(user),
        json={"type": "laboral", "title": "Caso 1", "description": "Detalle"},
    )

    assert create_response.status_code == 201
    case_id = create_response.get_json()["case"]["id"]

    list_response = client.get(f"/companies/{company.id}/cases", headers=auth_header_for(user))
    assert list_response.status_code == 200
    assert list_response.get_json()["cases"][0]["id"] == case_id

    update_response = client.patch(
        f"/companies/{company.id}/cases/{case_id}",
        headers=auth_header_for(user),
        json={"title": "Caso actualizado", "due_date": "2026-01-10"},
    )
    assert update_response.status_code == 200
    assert update_response.get_json()["case"]["title"] == "Caso actualizado"

    status_response = client.post(
        f"/companies/{company.id}/cases/{case_id}/status",
        headers=auth_header_for(user),
        json={"status": "in_progress"},
    )
    assert status_response.status_code == 200
    assert status_response.get_json()["case"]["status"] == "in_progress"

    assign_response = client.post(
        f"/companies/{company.id}/cases/{case_id}/assign",
        headers=auth_header_for(user),
        json={"responsible_user_id": assignee.id},
    )
    assert assign_response.status_code == 200
    assert assign_response.get_json()["case"]["responsible_user_id"] == assignee.id

    comment_response = client.post(
        f"/companies/{company.id}/cases/{case_id}/events/comment",
        headers=auth_header_for(user),
        json={"comment": "Seguimiento"},
    )
    assert comment_response.status_code == 201

    events_response = client.get(
        f"/companies/{company.id}/cases/{case_id}/events",
        headers=auth_header_for(user),
    )
    assert events_response.status_code == 200
    assert len(events_response.get_json()["events"]) >= 3


def test_case_acl_without_access_returns_404(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    company = create_company(db_session, tenant.id, "Alpha", "A-123")
    seed_rbac()

    assign_role(db_session, user, "Admin Cliente")

    response = client.get(f"/companies/{company.id}/cases", headers=auth_header_for(user))

    assert response.status_code == 404


def test_case_permission_without_role_returns_403(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    company = create_company(db_session, tenant.id, "Alpha", "A-123")
    seed_rbac()

    assign_access(db_session, user, company, "admin")

    response = client.get(f"/companies/{company.id}/cases", headers=auth_header_for(user))

    assert response.status_code == 403
    assert response.get_json()["message"] == "missing_permission"


def test_get_case_with_wrong_company_returns_404(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    company_a = create_company(db_session, tenant.id, "Alpha", "A-123")
    company_b = create_company(db_session, tenant.id, "Beta", "B-123")
    seed_rbac()

    assign_role(db_session, user, "Admin Cliente")
    assign_access(db_session, user, company_a, "admin")
    assign_access(db_session, user, company_b, "admin")

    create_response = client.post(
        f"/companies/{company_b.id}/cases",
        headers=auth_header_for(user),
        json={"type": "laboral", "title": "Caso B"},
    )
    case_id = create_response.get_json()["case"]["id"]

    response = client.get(
        f"/companies/{company_a.id}/cases/{case_id}",
        headers=auth_header_for(user),
    )

    assert response.status_code == 404


def test_create_case_invalid_payload_returns_400(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    company = create_company(db_session, tenant.id, "Alpha", "A-123")
    seed_rbac()

    assign_role(db_session, user, "Admin Cliente")
    assign_access(db_session, user, company, "admin")

    response = client.post(
        f"/companies/{company.id}/cases",
        headers=auth_header_for(user),
        json={"title": "Sin type"},
    )

    assert response.status_code == 400
    assert response.get_json()["message"] == "type_required"


def test_list_cases_filters_by_status_and_sorts_by_due_date(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    company = create_company(db_session, tenant.id, "Alpha", "A-123")
    seed_rbac()

    assign_role(db_session, user, "Admin Cliente")
    assign_access(db_session, user, company, "admin")

    response_a = client.post(
        f"/companies/{company.id}/cases",
        headers=auth_header_for(user),
        json={"type": "laboral", "title": "Case A", "due_date": "2026-01-20"},
    )
    response_b = client.post(
        f"/companies/{company.id}/cases",
        headers=auth_header_for(user),
        json={"type": "laboral", "title": "Case B", "due_date": "2026-01-10"},
    )

    case_a_id = response_a.get_json()["case"]["id"]
    case_b_id = response_b.get_json()["case"]["id"]

    client.post(
        f"/companies/{company.id}/cases/{case_b_id}/status",
        headers=auth_header_for(user),
        json={"status": "in_progress"},
    )

    sorted_response = client.get(
        f"/companies/{company.id}/cases?sort=due_date&order=asc",
        headers=auth_header_for(user),
    )
    assert sorted_response.status_code == 200
    sorted_ids = [item["id"] for item in sorted_response.get_json()["cases"]]
    assert sorted_ids[:2] == [case_b_id, case_a_id]

    status_response = client.get(
        f"/companies/{company.id}/cases?status=in_progress&sort=due_date&order=asc",
        headers=auth_header_for(user),
    )
    assert status_response.status_code == 200
    filtered_cases = status_response.get_json()["cases"]
    assert len(filtered_cases) == 1
    assert filtered_cases[0]["id"] == case_b_id


def test_list_cases_invalid_sort_or_order_returns_400(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    company = create_company(db_session, tenant.id, "Alpha", "A-123")
    seed_rbac()

    assign_role(db_session, user, "Admin Cliente")
    assign_access(db_session, user, company, "admin")

    invalid_sort_response = client.get(
        f"/companies/{company.id}/cases?sort=priority",
        headers=auth_header_for(user),
    )
    assert invalid_sort_response.status_code == 400
    assert invalid_sort_response.get_json()["message"] == "invalid_sort"

    invalid_order_response = client.get(
        f"/companies/{company.id}/cases?order=up",
        headers=auth_header_for(user),
    )
    assert invalid_order_response.status_code == 400
    assert invalid_order_response.get_json()["message"] == "invalid_order"
