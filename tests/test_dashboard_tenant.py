import uuid
from datetime import date, timedelta

import pytest

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.case import Case
from app.models.client import Client
from app.models.company import Company
from app.models.document import Document
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


def _auth_header(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.client_id)
    return {"Authorization": f"Bearer {token}"}


def _create_client(name: str) -> Client:
    tenant = Client(id=str(uuid.uuid4()), name=f"{name}-{uuid.uuid4()}", status="active", plan="basic")
    db.session.add(tenant)
    db.session.commit()
    return tenant


def _create_user(client_id: str, email: str) -> User:
    user = User(client_id=client_id, email=email, status="active")
    db.session.add(user)
    db.session.commit()
    return user


def _assign_role(user: User, role_name: str):
    role = Role.query.filter_by(name=role_name, scope="tenant", client_id=user.client_id).one()
    UserRoleRepository(db.session).assign_role(user.id, role.id)
    db.session.commit()


def test_dashboard_tenant_kpis_and_lists(client, db_session):
    tenant = _create_client("Tenant Op")
    seed_rbac()
    user = _create_user(tenant.id, "ops@example.com")
    _assign_role(user, "Admin Cliente")

    company = Company(client_id=tenant.id, name="Acme", tax_id="A-1")
    db.session.add(company)
    db.session.flush()

    person = Person(client_id=tenant.id, first_name="Ana", last_name="Lopez", document_number="123", status="pending_info")
    db.session.add(person)
    db.session.flush()

    db.session.add(
        PersonCompanyRelation(
            client_id=tenant.id,
            person_id=person.id,
            company_id=company.id,
            relation_type="owner",
            status="active",
            start_date=date.today() - timedelta(days=10),
        )
    )

    db.session.add(
        PersonRequest(
            client_id=tenant.id,
            person_id=person.id,
            company_id=company.id,
            request_type="dni",
            title="Subir DNI",
            status="pending",
            due_date=date.today() - timedelta(days=1),
            resolution_type="manual_review",
        )
    )

    db.session.add(
        Document(
            client_id=tenant.id,
            company_id=company.id,
            person_id=person.id,
            original_filename="dni.pdf",
            storage_path="/tmp/dni.pdf",
            doc_type="dni",
            status="pending",
        )
    )

    db.session.add(
        Case(
            client_id=tenant.id,
            company_id=company.id,
            person_id=person.id,
            type="onboarding",
            title="Onboarding",
            status="open",
            due_date=date.today() - timedelta(days=1),
        )
    )
    db.session.commit()

    response = client.get('/dashboard/tenant', headers=_auth_header(user))
    assert response.status_code == 200
    payload = response.get_json()

    assert payload['kpis']['persons_incomplete'] == 1
    assert payload['kpis']['requests_overdue'] == 1
    assert payload['kpis']['documents_pending_processing'] == 1
    assert payload['kpis']['cases_overdue'] == 1
    assert len(payload['attention_persons']) == 1
    assert len(payload['pending_requests']) == 1
    assert len(payload['recent_documents']) == 1
    assert len(payload['cases_attention']) == 1

    audit = AuditLog.query.filter_by(client_id=tenant.id, action='dashboard_viewed').all()
    assert len(audit) == 1


def test_dashboard_tenant_isolation(client, db_session):
    tenant_a = _create_client('A')
    tenant_b = _create_client('B')
    seed_rbac()
    user_a = _create_user(tenant_a.id, 'a@example.com')
    _assign_role(user_a, 'Admin Cliente')

    person_b = Person(client_id=tenant_b.id, first_name='B', last_name='Only', document_number='B1', status='pending_info')
    db.session.add(person_b)
    db.session.flush()
    db.session.add(PersonRequest(client_id=tenant_b.id, person_id=person_b.id, request_type='x', title='x', status='pending', resolution_type='manual_review'))
    db.session.commit()

    response = client.get('/dashboard/tenant', headers=_auth_header(user_a))
    assert response.status_code == 200
    payload = response.get_json()
    assert payload['kpis']['persons_total'] == 0
    assert payload['kpis']['requests_pending'] == 0
    assert payload['attention_persons'] == []
