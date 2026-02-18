from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest
from werkzeug.security import generate_password_hash

from app.cli import seed_rbac
from app.extensions import db
from app.models.client import Client
from app.models.company import Company
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.modules.cases.service import CaseService
from app.repositories.user_company_access_repository import UserCompanyAccessRepository
from app.repositories.user_role_repository import UserRoleRepository


@dataclass
class DocumentScenario:
    client_a_id: str
    client_b_id: str
    user_admin_a_id: str
    user_viewer_a_id: str
    user_no_acl_a_id: str
    user_admin_b_id: str
    company_a_id: str
    case_a_id: str
    company_b_id: str
    case_b_id: str


@pytest.fixture()
def db_session(app):
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
        db.drop_all()


def _create_client(db_session, name: str) -> Client:
    client = Client(name=name, status="active")
    db_session.add(client)
    db_session.commit()
    return client


def _create_user(db_session, client_id: str, email: str, password: str = "Passw0rd!") -> User:
    user = User(
        client_id=client_id,
        email=email,
        status="active",
        password_hash=generate_password_hash(password),
    )
    db_session.add(user)
    db_session.commit()
    return user


def _create_company(db_session, client_id: str, name: str, tax_id: str) -> Company:
    company = Company(client_id=client_id, name=name, tax_id=tax_id)
    db_session.add(company)
    db_session.commit()
    return company


def _create_case(client_id: str, company_id: str, actor_user_id: str, title: str) -> str:
    case = CaseService().create_case(
        client_id=client_id,
        company_id=company_id,
        actor_user_id=actor_user_id,
        payload={"title": title},
    )
    db.session.commit()
    return case.id


def _assign_role(db_session, user: User, role_name: str) -> None:
    role = Role.query.filter_by(name=role_name, scope="tenant", client_id=user.client_id).one()
    UserRoleRepository(db_session).assign_role(user.id, role.id)
    db_session.commit()


def _assign_access(db_session, user: User, company: Company, access_level: str) -> None:
    UserCompanyAccessRepository(db_session).upsert_access(user.id, company.id, user.client_id, access_level)
    db_session.commit()


@pytest.fixture()
def login(client) -> Callable[[str, str, str | None], dict[str, str]]:
    def _login(email: str, password: str, client_id: str | None = None) -> dict[str, str]:
        payload: dict[str, str] = {"email": email, "password": password}
        if client_id is not None:
            payload["client_id"] = client_id

        response = client.post("/auth/login", json=payload)
        assert response.status_code == 200
        token = response.get_json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return _login


@pytest.fixture()
def document_scenario(app, db_session) -> DocumentScenario:
    with app.app_context():
        client_a = _create_client(db_session, "Tenant A")
        client_b = _create_client(db_session, "Tenant B")
        seed_rbac()

        user_admin_a = _create_user(db_session, client_a.id, "admina@test.com")
        user_viewer_a = _create_user(db_session, client_a.id, "viewera@test.com")
        user_no_acl_a = _create_user(db_session, client_a.id, "noacla@test.com")
        user_admin_b = _create_user(db_session, client_b.id, "adminb@test.com")

        company_a = _create_company(db_session, client_a.id, "A1", "A1")
        company_b = _create_company(db_session, client_b.id, "B1", "B1")

        case_a_id = _create_case(client_a.id, company_a.id, user_admin_a.id, "Caso A")
        case_b_id = _create_case(client_b.id, company_b.id, user_admin_b.id, "Caso B")

        _assign_role(db_session, user_admin_a, "Admin Cliente")
        _assign_role(db_session, user_viewer_a, "Operativo")
        _assign_role(db_session, user_admin_b, "Admin Cliente")

        _assign_access(db_session, user_admin_a, company_a, "admin")
        _assign_access(db_session, user_viewer_a, company_a, "viewer")
        _assign_access(db_session, user_admin_b, company_b, "admin")

        return DocumentScenario(
            client_a_id=client_a.id,
            client_b_id=client_b.id,
            user_admin_a_id=user_admin_a.id,
            user_viewer_a_id=user_viewer_a.id,
            user_no_acl_a_id=user_no_acl_a.id,
            user_admin_b_id=user_admin_b.id,
            company_a_id=company_a.id,
            case_a_id=case_a_id,
            company_b_id=company_b.id,
            case_b_id=case_b_id,
        )


@pytest.fixture()
def role_without_permission_factory(app, db_session):
    with app.app_context():

        def _factory(*, client_id: str, name: str, allowed_permission_codes: list[str]) -> Role:
            role = Role(name=name, scope="tenant", client_id=client_id)
            db_session.add(role)
            db_session.flush()
            if allowed_permission_codes:
                permissions = (
                    Permission.query.filter(Permission.code.in_(allowed_permission_codes))
                    .order_by(Permission.code)
                    .all()
                )
                role.permissions = permissions
            db_session.commit()
            return role

        return _factory


@pytest.fixture()
def user_factory(app, db_session):
    with app.app_context():

        def _factory(*, client_id: str, email: str, password: str = "Passw0rd!") -> User:
            return _create_user(db_session, client_id=client_id, email=email, password=password)

        return _factory


@pytest.fixture()
def access_factory(app, db_session):
    with app.app_context():

        def _factory(*, user: User, company: Company, access_level: str) -> None:
            _assign_access(db_session, user=user, company=company, access_level=access_level)

        return _factory


@pytest.fixture()
def role_factory(app, db_session):
    with app.app_context():

        def _factory(*, user: User, role_name: str) -> None:
            _assign_role(db_session, user=user, role_name=role_name)

        return _factory
