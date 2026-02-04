import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.client import Client
from app.models.permission import Permission
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


def create_client(db_session) -> Client:
    client = Client(name="Acme")
    db_session.add(client)
    db_session.commit()
    return client


def create_user(db_session, client_id: str) -> User:
    user = User(client_id=client_id, email="user@example.com", status="active")
    db_session.add(user)
    db_session.commit()
    return user


def test_role_permission_assignment(db_session):
    tenant = create_client(db_session)
    permission_read = Permission(code="company.read", description="Read companies")
    permission_write = Permission(code="company.write", description="Write companies")
    role = Role(
        name="Tenant Admin",
        scope="tenant",
        client_id=tenant.id,
        permissions=[permission_read, permission_write],
    )

    db_session.add(role)
    db_session.commit()

    stored_role = db_session.query(Role).filter_by(name="Tenant Admin").one()
    codes = {permission.code for permission in stored_role.permissions}
    assert codes == {"company.read", "company.write"}


def test_user_role_assignment(db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id)
    role = Role(name="Tenant Viewer", scope="tenant", client_id=tenant.id)
    db_session.add(role)
    db_session.commit()

    repository = UserRoleRepository(db_session)
    repository.assign_role(user.id, role.id)
    db_session.commit()

    db_session.refresh(user)
    assert {assigned_role.id for assigned_role in user.roles} == {role.id}


def test_role_scope_constraint(db_session):
    tenant = create_client(db_session)

    invalid_platform = Role(name="Invalid Platform", scope="platform", client_id=tenant.id)
    db_session.add(invalid_platform)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    invalid_tenant = Role(name="Invalid Tenant", scope="tenant", client_id=None)
    db_session.add(invalid_tenant)
    with pytest.raises(IntegrityError):
        db_session.commit()
