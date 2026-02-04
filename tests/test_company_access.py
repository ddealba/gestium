import pytest
from sqlalchemy import select

from app.common.access_levels import AccessLevel, access_level_ge
from app.extensions import db
from app.models.client import Client
from app.models.user import User
from app.models.user_company_access import UserCompanyAccess
from app.repositories.user_company_access_repository import UserCompanyAccessRepository


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


def create_user(db_session, client_id: str) -> User:
    user = User(client_id=client_id, email="user@example.com", status="active")
    db_session.add(user)
    db_session.commit()
    return user


def test_access_level_comparisons():
    assert access_level_ge(AccessLevel.viewer, AccessLevel.viewer)
    assert not access_level_ge(AccessLevel.viewer, AccessLevel.operator)
    assert access_level_ge(AccessLevel.manager, AccessLevel.operator)
    assert access_level_ge("admin", "manager")


def test_upsert_access_updates_level(db_session):
    tenant = create_client(db_session, "Acme")
    user = create_user(db_session, tenant.id)

    repository = UserCompanyAccessRepository(db_session)
    access = repository.upsert_access(user.id, "company-1", tenant.id, AccessLevel.viewer.value)
    db_session.commit()

    access = repository.upsert_access(user.id, "company-1", tenant.id, AccessLevel.manager.value)
    db_session.commit()

    rows = db_session.execute(
        select(UserCompanyAccess).where(
            UserCompanyAccess.user_id == user.id,
            UserCompanyAccess.company_id == "company-1",
            UserCompanyAccess.client_id == tenant.id,
        )
    ).scalars().all()

    assert len(rows) == 1
    assert rows[0].access_level == AccessLevel.manager.value


def test_repository_filters_by_client_id(db_session):
    tenant = create_client(db_session, "Acme")
    other_tenant = create_client(db_session, "Beta")
    user = create_user(db_session, tenant.id)

    repository = UserCompanyAccessRepository(db_session)
    repository.upsert_access(user.id, "company-1", tenant.id, AccessLevel.viewer.value)
    db_session.commit()

    assert repository.get_user_access(user.id, "company-1", other_tenant.id) is None
