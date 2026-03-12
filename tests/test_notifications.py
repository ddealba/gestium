from __future__ import annotations

import io
import uuid
from datetime import date, timedelta

import pytest

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.client import Client
from app.models.notification import Notification
from app.models.person import Person
from app.models.role import Role
from app.models.user import User
from app.repositories.user_role_repository import UserRoleRepository


def auth_header(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user.id, user.client_id)}"}


@pytest.fixture()
def db_session(app):
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
        db.drop_all()


def assign_role(user: User, role_name: str) -> None:
    role = Role.query.filter_by(name=role_name, scope="tenant", client_id=user.client_id).one()
    UserRoleRepository(db.session).assign_role(user.id, role.id)
    db.session.commit()


def test_notifications_flow(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)

        tenant = Client(name=f"Tenant {uuid.uuid4()}", status="active")
        other_tenant = Client(name=f"Other {uuid.uuid4()}", status="active")
        db.session.add_all([tenant, other_tenant])
        db.session.flush()
        seed_rbac()

        person = Person(client_id=tenant.id, first_name="Portal", last_name="User", document_number="D-1", status="active")
        person_other = Person(client_id=tenant.id, first_name="Other", last_name="Portal", document_number="D-2", status="active")
        db.session.add_all([person, person_other])
        db.session.flush()


        internal = User(client_id=tenant.id, email="internal@tenant.com", password_hash="x", status="active")
        internal_other = User(client_id=tenant.id, email="internal2@tenant.com", password_hash="x", status="active")
        portal_user = User(client_id=tenant.id, email="portal@tenant.com", password_hash="x", status="active", user_type="portal", person_id=person.id)
        portal_other = User(client_id=tenant.id, email="portal2@tenant.com", password_hash="x", status="active", user_type="portal", person_id=person_other.id)

        outsider = User(client_id=other_tenant.id, email="out@other.com", password_hash="x", status="active")
        db.session.add_all([internal, internal_other, portal_user, portal_other, outsider])
        db.session.commit()
        assign_role(internal, "Admin Cliente")

        create_response = client.post(
            f"/persons/{person.id}/requests",
            headers=auth_header(internal),
            json={
                "request_type": "upload_document",
                "title": "Sube tu DNI",
                "description": "Necesitamos copia de tu DNI",
                "due_date": (date.today() + timedelta(days=30)).isoformat(),
                "resolution_type": "document_upload",
            },
        )
        assert create_response.status_code == 201
        request_id = create_response.get_json()["request"]["id"]

        portal_notifications = client.get("/portal/api/notifications", headers=auth_header(portal_user))
        assert portal_notifications.status_code == 200
        payload = portal_notifications.get_json()
        assert any(item["type"] == "request_created" and item["entity_id"] == request_id for item in payload)

        other_portal_list = client.get("/portal/api/notifications", headers=auth_header(portal_other))
        assert other_portal_list.status_code == 200
        assert other_portal_list.get_json() == []

        request_created_item = next(item for item in payload if item["type"] == "request_created")

        read_response = client.post(f"/portal/api/notifications/{request_created_item['id']}/read", headers=auth_header(portal_user))
        assert read_response.status_code == 200
        assert read_response.get_json()["status"] == "read"

        dismiss_response = client.post(f"/portal/api/notifications/{request_created_item['id']}/dismiss", headers=auth_header(portal_user))
        assert dismiss_response.status_code == 200
        assert dismiss_response.get_json()["status"] == "dismissed"

        forbidden_cross = client.post(f"/portal/api/notifications/{request_created_item['id']}/read", headers=auth_header(portal_other))
        assert forbidden_cross.status_code == 404

        upload_response = client.post(
            f"/portal/api/requests/{request_id}/upload",
            headers=auth_header(portal_user),
            data={"file": (io.BytesIO(b"%PDF-1.4 person request"), "dni.pdf")},
            content_type="multipart/form-data",
        )
        assert upload_response.status_code == 200

        backoffice_notifications = client.get("/api/notifications", headers=auth_header(internal))
        assert backoffice_notifications.status_code == 200
        bo_payload = backoffice_notifications.get_json()
        assert any(item["type"] == "document_uploaded" for item in bo_payload)

        first_bo_id = bo_payload[0]["id"]
        mark_bo = client.post(f"/api/notifications/{first_bo_id}/read", headers=auth_header(internal))
        assert mark_bo.status_code == 200
        assert mark_bo.get_json()["status"] == "read"

        bo_other = client.get("/api/notifications", headers=auth_header(internal_other))
        assert bo_other.status_code == 200
        assert bo_other.get_json() == []

        cross_tenant = client.get("/api/notifications", headers=auth_header(outsider))
        assert cross_tenant.status_code == 200
        assert cross_tenant.get_json() == []

        assert db.session.query(Notification).filter(Notification.client_id == tenant.id).count() >= 2
