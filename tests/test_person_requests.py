from __future__ import annotations

import io
import uuid
from datetime import date

import pytest

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.case import Case
from app.models.client import Client
from app.models.company import Company
from app.models.document import Document
from app.models.employee import Employee
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


def test_person_request_backoffice_and_portal_flow(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)

        tenant = Client(name=f"Tenant {uuid.uuid4()}", status="active")
        other_tenant = Client(name=f"Other {uuid.uuid4()}", status="active")
        db.session.add_all([tenant, other_tenant])
        db.session.flush()

        seed_rbac()

        person = Person(client_id=tenant.id, first_name="Portal", last_name="User", document_number="P-1", status="active")
        other_person = Person(client_id=tenant.id, first_name="Other", last_name="User", document_number="P-2", status="active")
        foreign_person = Person(client_id=other_tenant.id, first_name="Foreign", last_name="User", document_number="P-3", status="active")
        db.session.add_all([person, other_person, foreign_person])
        db.session.flush()

        company = Company(client_id=tenant.id, name="Empresa", tax_id="TAX-1", status="active")
        db.session.add(company)
        db.session.flush()

        case = Case(client_id=tenant.id, company_id=company.id, person_id=person.id, title="Caso", type="tax", status="open")
        db.session.add(case)
        db.session.flush()

        employee = Employee(
            client_id=tenant.id,
            company_id=company.id,
            person_id=person.id,
            full_name="Portal User",
            status="active",
            start_date=date(2025, 1, 1),
        )
        db.session.add(employee)
        db.session.flush()

        internal = User(client_id=tenant.id, email="internal@tenant.com", password_hash="x", status="active")
        portal_user = User(client_id=tenant.id, email="portal@tenant.com", password_hash="x", status="active", user_type="portal", person_id=person.id)
        portal_other = User(client_id=tenant.id, email="other@tenant.com", password_hash="x", status="active", user_type="portal", person_id=other_person.id)
        db.session.add_all([internal, portal_user, portal_other])
        db.session.commit()

        assign_role(internal, "Admin Cliente")

        create_response = client.post(
            f"/persons/{person.id}/requests",
            headers=auth_header(internal),
            json={
                "request_type": "upload_document",
                "title": "Sube tu DNI",
                "description": "Necesitamos copia de tu DNI",
                "due_date": "2026-03-25",
                "resolution_type": "document_upload",
            },
        )
        assert create_response.status_code == 201
        request_id = create_response.get_json()["request"]["id"]

        list_response = client.get(f"/persons/{person.id}/requests", headers=auth_header(internal))
        assert list_response.status_code == 200
        assert len(list_response.get_json()["items"]) == 1

        portal_list = client.get("/portal/api/requests", headers=auth_header(portal_user))
        assert portal_list.status_code == 200
        assert {item["id"] for item in portal_list.get_json()} == {request_id}

        forbidden_other = client.get(f"/portal/api/requests/{request_id}", headers=auth_header(portal_other))
        assert forbidden_other.status_code == 403

        upload_response = client.post(
            f"/portal/api/requests/{request_id}/upload",
            headers=auth_header(portal_user),
            data={"file": (io.BytesIO(b"%PDF-1.4 person request"), "dni.pdf")},
            content_type="multipart/form-data",
        )
        assert upload_response.status_code == 200
        assert upload_response.get_json()["request"]["status"] == "resolved"

        docs = db.session.query(Document).filter(Document.person_id == person.id).all()
        assert len(docs) == 1

        create_submit = client.post(
            f"/persons/{person.id}/requests",
            headers=auth_header(internal),
            json={
                "request_type": "confirm_information",
                "title": "Confirma datos",
                "resolution_type": "form_submission",
            },
        )
        submit_id = create_submit.get_json()["request"]["id"]

        submit_response = client.post(
            f"/portal/api/requests/{submit_id}/submit",
            headers=auth_header(portal_user),
            json={"payload": {"phone": "600123123", "notes": "Datos actualizados"}},
        )
        assert submit_response.status_code == 200
        assert submit_response.get_json()["request"]["status"] == "resolved"
        assert submit_response.get_json()["request"]["resolution_payload"]["phone"] == "600123123"

        cross_tenant = client.get(f"/persons/{foreign_person.id}/requests", headers=auth_header(internal))
        assert cross_tenant.status_code == 404
