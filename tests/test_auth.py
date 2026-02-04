import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.client import Client
from app.models.user import User


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


def test_login_returns_token(client, db_session):
    tenant = create_client(db_session)
    create_user(db_session, tenant.id, "user@example.com", "supersecret")

    response = client.post(
        "/auth/login",
        json={"email": "USER@example.com", "password": "supersecret", "client_id": tenant.id},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["token_type"] == "Bearer"
    assert payload["expires_in"] == 3600
    assert payload["access_token"]


def test_auth_me_returns_user(client, db_session):
    tenant = create_client(db_session)
    user = create_user(db_session, tenant.id, "me@example.com", "supersecret")

    login_response = client.post(
        "/auth/login",
        json={"email": "me@example.com", "password": "supersecret", "client_id": tenant.id},
    )
    token = login_response.get_json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.get_json() == {
        "id": user.id,
        "email": "me@example.com",
        "client_id": tenant.id,
        "status": "active",
    }


def test_login_invalid_password(client, db_session):
    tenant = create_client(db_session)
    create_user(db_session, tenant.id, "user@example.com", "supersecret")

    response = client.post(
        "/auth/login",
        json={"email": "user@example.com", "password": "wrong", "client_id": tenant.id},
    )

    assert response.status_code == 401
    assert response.get_json()["message"] == "invalid_credentials"


def test_login_disabled_user(client, db_session):
    tenant = create_client(db_session)
    create_user(db_session, tenant.id, "disabled@example.com", "supersecret", status="disabled")

    response = client.post(
        "/auth/login",
        json={"email": "disabled@example.com", "password": "supersecret", "client_id": tenant.id},
    )

    assert response.status_code == 403
    assert response.get_json()["message"] == "user_inactive"
