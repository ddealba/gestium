import hashlib

import pytest

from app.extensions import db
from app.models.client import Client
from app.models.user import User
from app.models.user_invitation import UserInvitation


@pytest.fixture()
def db_session(app):
    app.config["ALLOW_X_CLIENT_ID_HEADER"] = True
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


def test_invite_creates_user_and_invitation(client, db_session):
    tenant = create_client(db_session)
    response = client.post(
        "/auth/invite",
        json={"email": "User@Example.com"},
        headers={"X-Client-Id": tenant.id},
    )

    assert response.status_code == 201
    payload = response.get_json()
    assert "invite_token" in payload
    assert "expires_at" in payload

    user = db_session.query(User).filter_by(client_id=tenant.id).one()
    assert user.email == "user@example.com"
    assert user.status == "invited"

    invitation = db_session.query(UserInvitation).filter_by(client_id=tenant.id).one()
    assert invitation.email == "user@example.com"
    assert invitation.used_at is None
    assert invitation.token_hash != payload["invite_token"]
    assert invitation.token_hash == hashlib.sha256(payload["invite_token"].encode("utf-8")).hexdigest()


def test_activate_consumes_invitation(client, db_session):
    tenant = create_client(db_session)
    invite_response = client.post(
        "/auth/invite",
        json={"email": "activate@example.com"},
        headers={"X-Client-Id": tenant.id},
    )
    token = invite_response.get_json()["invite_token"]

    activate_response = client.post(
        "/auth/activate",
        json={"token": token, "password": "supersecret"},
        headers={"X-Client-Id": tenant.id},
    )

    assert activate_response.status_code == 200
    assert activate_response.get_json() == {"status": "active"}

    user = db_session.query(User).filter_by(client_id=tenant.id, email="activate@example.com").one()
    invitation = db_session.query(UserInvitation).filter_by(client_id=tenant.id, email="activate@example.com").one()
    assert user.status == "active"
    assert invitation.used_at is not None


def test_activate_twice_fails(client, db_session):
    tenant = create_client(db_session)
    invite_response = client.post(
        "/auth/invite",
        json={"email": "double@example.com"},
        headers={"X-Client-Id": tenant.id},
    )
    token = invite_response.get_json()["invite_token"]

    first_response = client.post(
        "/auth/activate",
        json={"token": token, "password": "supersecret"},
        headers={"X-Client-Id": tenant.id},
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/auth/activate",
        json={"token": token, "password": "supersecret"},
        headers={"X-Client-Id": tenant.id},
    )

    assert second_response.status_code == 400
    assert second_response.get_json()["message"] == "token_used"
