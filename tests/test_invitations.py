import hashlib

import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.client import Client
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.models.user_invitation import UserInvitation
from app.repositories.user_role_repository import UserRoleRepository


@pytest.fixture()
def db_session(app):
    app.config["ALLOW_X_CLIENT_ID_HEADER"] = False
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


def create_user(db_session, client_id: str, email: str, password: str, status: str = "active") -> User:
    user = User(
        client_id=client_id,
        email=email,
        status=status,
        password_hash=generate_password_hash(password),
    )
    db_session.add(user)
    db_session.commit()
    return user


def grant_invite_permission(db_session, user: User, client_id: str) -> None:
    permission = Permission(code="tenant.users.invite", description="Invite users")
    role = Role(name="Tenant Invite", scope="tenant", client_id=client_id, permissions=[permission])
    db_session.add(role)
    db_session.commit()
    UserRoleRepository(db_session).assign_role(user.id, role.id)
    db_session.commit()


def login_user(client, email: str, password: str, client_id: str) -> str:
    response = client.post(
        "/auth/login",
        json={"email": email, "password": password, "client_id": client_id},
    )
    assert response.status_code == 200
    return response.get_json()["access_token"]


def test_invite_requires_auth(client, db_session):
    create_client(db_session)
    response = client.post("/auth/invite", json={"email": "user@example.com"})

    assert response.status_code == 401
    assert response.get_json()["message"] == "missing_token"


def test_invite_requires_permission(client, db_session):
    tenant = create_client(db_session)
    create_user(db_session, tenant.id, "owner@example.com", "supersecret")
    token = login_user(client, "owner@example.com", "supersecret", tenant.id)

    response = client.post(
        "/auth/invite",
        json={"email": "user@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.get_json()["message"] == "missing_permission"


def test_invite_creates_user_and_invitation(client, db_session):
    tenant = create_client(db_session)
    inviter = create_user(db_session, tenant.id, "inviter@example.com", "supersecret")
    grant_invite_permission(db_session, inviter, tenant.id)
    token = login_user(client, "inviter@example.com", "supersecret", tenant.id)
    response = client.post(
        "/auth/invite",
        json={"email": "User@Example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert "invite_token" in payload
    assert "expires_at" in payload

    user = db_session.query(User).filter_by(client_id=tenant.id, email="user@example.com").one()
    assert user.email == "user@example.com"
    assert user.status == "invited"

    invitation = (
        db_session.query(UserInvitation)
        .filter_by(client_id=tenant.id, email="user@example.com")
        .one()
    )
    assert invitation.email == "user@example.com"
    assert invitation.used_at is None
    assert invitation.token_hash != payload["invite_token"]
    assert invitation.token_hash == hashlib.sha256(payload["invite_token"].encode("utf-8")).hexdigest()


def test_activate_works_without_x_client_id_header(client, db_session):
    tenant = create_client(db_session)
    inviter = create_user(db_session, tenant.id, "inviter@example.com", "supersecret")
    grant_invite_permission(db_session, inviter, tenant.id)
    token = login_user(client, "inviter@example.com", "supersecret", tenant.id)
    invite_response = client.post(
        "/auth/invite",
        json={"email": "activate@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    invite_token = invite_response.get_json()["invite_token"]

    activate_response = client.post(
        "/auth/activate",
        json={"token": invite_token, "password": "supersecret"},
    )

    assert activate_response.status_code == 200
    assert activate_response.get_json() == {"status": "active"}

    user = db_session.query(User).filter_by(client_id=tenant.id, email="activate@example.com").one()
    invitation = db_session.query(UserInvitation).filter_by(client_id=tenant.id, email="activate@example.com").one()
    assert user.status == "active"
    assert invitation.used_at is not None


def test_activate_cannot_be_reused(client, db_session):
    tenant = create_client(db_session)
    inviter = create_user(db_session, tenant.id, "inviter@example.com", "supersecret")
    grant_invite_permission(db_session, inviter, tenant.id)
    token = login_user(client, "inviter@example.com", "supersecret", tenant.id)
    invite_response = client.post(
        "/auth/invite",
        json={"email": "double@example.com"},
        headers={"Authorization": f"Bearer {token}"},
    )
    invite_token = invite_response.get_json()["invite_token"]

    first_response = client.post(
        "/auth/activate",
        json={"token": invite_token, "password": "supersecret"},
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/auth/activate",
        json={"token": invite_token, "password": "supersecret"},
    )

    assert second_response.status_code == 400
    assert second_response.get_json()["message"] == "token_used"
