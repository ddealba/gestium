from io import BytesIO
from uuid import uuid4

import pytest
from werkzeug.datastructures import FileStorage

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.client import Client
from app.models.company import Company
from app.models.document_extraction import DocumentExtraction
from app.models.employee import Employee
from app.models.person import Person
from app.models.role import Role
from app.models.user import User
from app.modules.cases.service import CaseService
from app.modules.documents.service import DocumentModuleService
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
    client = Client(name=f"Acme-{uuid4()}")
    db_session.add(client)
    db_session.commit()
    return client


def create_user(db_session, client_id: str, email: str = "user@example.com") -> User:
    user = User(client_id=client_id, email=email, status="active")
    db_session.add(user)
    db_session.commit()
    return user


def create_company(db_session, client_id: str, name: str = "Alpha", tax_id: str = "A-123") -> Company:
    company = Company(client_id=client_id, name=name, tax_id=tax_id)
    db_session.add(company)
    db_session.commit()
    return company


def create_person(db_session, client_id: str, idx: str = "1") -> Person:
    person = Person(
        client_id=client_id,
        first_name=f"Nombre{idx}",
        last_name=f"Apellido{idx}",
        document_number=f"DOC-{idx}",
        status="active",
    )
    db_session.add(person)
    db_session.commit()
    return person


def create_employee(db_session, client_id: str, company_id: str, person_id: str | None = None) -> Employee:
    from datetime import date

    employee = Employee(
        client_id=client_id,
        company_id=company_id,
        person_id=person_id,
        full_name="Empleado Test",
        employee_ref="EMP-1",
        status="active",
        start_date=date.today(),
    )
    db_session.add(employee)
    db_session.commit()
    return employee


def auth_header_for(user: User) -> dict[str, str]:
    token = create_access_token(user.id, user.client_id)
    return {"Authorization": f"Bearer {token}"}


def assign_role(db_session, user: User, role_name: str) -> None:
    role = Role.query.filter_by(name=role_name, scope="tenant", client_id=user.client_id).one()
    UserRoleRepository(db_session).assign_role(user.id, role.id)
    db_session.commit()


def assign_access(db_session, user: User, company: Company, level: str) -> None:
    UserCompanyAccessRepository(db_session).upsert_access(user.id, company.id, user.client_id, level)
    db_session.commit()


def create_case(tenant_id: str, company_id: str, actor_user_id: str) -> str:
    case = CaseService().create_case(
        client_id=tenant_id,
        company_id=company_id,
        actor_user_id=actor_user_id,
        payload={"title": "Caso documentos"},
    )
    db.session.commit()
    return case.id


def test_upload_document_scoped_endpoint_returns_safe_metadata(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id)
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, user.id)
        assign_role(db_session, user, "Operativo")
        assign_access(db_session, user, company, "operator")

        response = client.post(
            f"/companies/{company.id}/cases/{case_id}/documents",
            headers=auth_header_for(user),
            data={
                "doc_type": "evidence",
                "file": (BytesIO(b"%PDF-1.4 content"), "contrato.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 201
        document = response.get_json()["document"]
        assert document["original_filename"] == "contrato.pdf"
        assert document["doc_type"] == "evidence"
        assert "storage_path" not in document


def test_list_documents_returns_only_documents_from_case(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id)
        company = create_company(db_session, tenant.id)
        case_a_id = create_case(tenant.id, company.id, user.id)
        case_b_id = create_case(tenant.id, company.id, user.id)
        assign_role(db_session, user, "Operativo")
        assign_access(db_session, user, company, "viewer")

        service = DocumentModuleService()
        service.upload_case_document(
            client_id=tenant.id,
            company_id=company.id,
            case_id=case_a_id,
            actor_user_id=user.id,
            file=FileStorage(
                stream=BytesIO(b"%PDF-1.4 A"),
                filename="case-a.pdf",
                content_type="application/pdf",
            ),
        )
        service.upload_case_document(
            client_id=tenant.id,
            company_id=company.id,
            case_id=case_b_id,
            actor_user_id=user.id,
            file=FileStorage(
                stream=BytesIO(b"%PDF-1.4 B"),
                filename="case-b.pdf",
                content_type="application/pdf",
            ),
        )
        db.session.commit()

        response = client.get(
            f"/companies/{company.id}/cases/{case_a_id}/documents",
            headers=auth_header_for(user),
        )

        assert response.status_code == 200
        documents = response.get_json()["items"]
        assert len(documents) == 1
        assert documents[0]["original_filename"] == "case-a.pdf"


def test_download_document_without_company_access_returns_404(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        uploader = create_user(db_session, tenant.id, email="uploader@example.com")
        reader = create_user(db_session, tenant.id, email="reader@example.com")
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, uploader.id)
        assign_role(db_session, uploader, "Operativo")
        assign_access(db_session, uploader, company, "operator")

        assign_role(db_session, reader, "Operativo")

        document = DocumentModuleService().upload_case_document(
            client_id=tenant.id,
            company_id=company.id,
            case_id=case_id,
            actor_user_id=uploader.id,
            file=FileStorage(
                stream=BytesIO(b"%PDF-1.4 Secret"),
                filename="secret.pdf",
                content_type="application/pdf",
            ),
        )
        db.session.commit()

        response = client.get(
            f"/documents/{document.id}/download",
            headers=auth_header_for(reader),
        )

        assert response.status_code == 404
        assert response.get_json()["message"] == "document_not_found"


def test_upload_happy_path_list_and_download(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id, email="operator@example.com")
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, user.id)
        assign_role(db_session, user, "Admin Cliente")
        assign_access(db_session, user, company, "operator")

        upload_response = client.post(
            f"/companies/{company.id}/cases/{case_id}/documents",
            headers=auth_header_for(user),
            data={
                "doc_type": "evidence",
                "file": (BytesIO(b"%PDF-1.4 upload"), "ok.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )

        assert upload_response.status_code == 201
        document_id = upload_response.get_json()["document"]["id"]

        list_response = client.get(
            f"/companies/{company.id}/cases/{case_id}/documents",
            headers=auth_header_for(user),
        )

        assert list_response.status_code == 200
        documents = list_response.get_json()["items"]
        assert len(documents) == 1
        assert documents[0]["id"] == document_id

        download_response = client.get(
            f"/documents/{document_id}/download",
            headers=auth_header_for(user),
        )

        assert download_response.status_code == 200
        assert download_response.headers["Content-Type"].startswith("application/pdf")


def test_upload_without_document_upload_permission_returns_403(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id, email="norole@example.com")
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, user.id)
        assign_access(db_session, user, company, "operator")

        response = client.post(
            f"/companies/{company.id}/cases/{case_id}/documents",
            headers=auth_header_for(user),
            data={
                "file": (BytesIO(b"%PDF-1.4 upload"), "no-permission.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 403


def test_upload_with_viewer_acl_returns_403(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id, email="viewer-acl@example.com")
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, user.id)
        assign_role(db_session, user, "Operativo")
        assign_access(db_session, user, company, "viewer")

        response = client.post(
            f"/companies/{company.id}/cases/{case_id}/documents",
            headers=auth_header_for(user),
            data={
                "file": (BytesIO(b"%PDF-1.4 upload"), "viewer.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 403


def test_cross_tenant_list_documents_returns_404(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant_a = create_client(db_session)
        tenant_b = create_client(db_session)
        seed_rbac()

        user_a = create_user(db_session, tenant_a.id, email="tenant-a@example.com")
        user_b = create_user(db_session, tenant_b.id, email="tenant-b@example.com")

        company_a = create_company(db_session, tenant_a.id, name="Alpha A", tax_id="A-001")
        company_b = create_company(db_session, tenant_b.id, name="Alpha B", tax_id="B-001")
        case_a_id = create_case(tenant_a.id, company_a.id, user_a.id)

        assign_role(db_session, user_a, "Operativo")
        assign_access(db_session, user_a, company_a, "operator")

        assign_role(db_session, user_b, "Admin Cliente")
        assign_access(db_session, user_b, company_b, "operator")

        upload_response = client.post(
            f"/companies/{company_a.id}/cases/{case_a_id}/documents",
            headers=auth_header_for(user_a),
            data={
                "file": (BytesIO(b"%PDF-1.4 upload"), "tenant-a.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )
        assert upload_response.status_code == 201

        response = client.get(
            f"/companies/{company_a.id}/cases/{case_a_id}/documents",
            headers=auth_header_for(user_b),
        )

        assert response.status_code == 404


def test_cross_tenant_download_returns_404(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant_a = create_client(db_session)
        tenant_b = create_client(db_session)
        seed_rbac()

        user_a = create_user(db_session, tenant_a.id, email="owner@example.com")
        user_b = create_user(db_session, tenant_b.id, email="intruder@example.com")

        company_a = create_company(db_session, tenant_a.id, name="Owner Co", tax_id="OA-001")
        company_b = create_company(db_session, tenant_b.id, name="Intruder Co", tax_id="IB-001")
        case_a_id = create_case(tenant_a.id, company_a.id, user_a.id)

        assign_role(db_session, user_a, "Operativo")
        assign_access(db_session, user_a, company_a, "operator")

        assign_role(db_session, user_b, "Admin Cliente")
        assign_access(db_session, user_b, company_b, "operator")

        upload_response = client.post(
            f"/companies/{company_a.id}/cases/{case_a_id}/documents",
            headers=auth_header_for(user_a),
            data={
                "file": (BytesIO(b"%PDF-1.4 upload"), "tenant-a.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )
        assert upload_response.status_code == 201
        document_id = upload_response.get_json()["document"]["id"]

        response = client.get(
            f"/documents/{document_id}/download",
            headers=auth_header_for(user_b),
        )

        assert response.status_code == 404


def test_upload_validation_missing_or_empty_file_returns_400(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id, email="validator@example.com")
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, user.id)
        assign_role(db_session, user, "Operativo")
        assign_access(db_session, user, company, "operator")

        missing_response = client.post(
            f"/companies/{company.id}/cases/{case_id}/documents",
            headers=auth_header_for(user),
            data={"doc_type": "evidence"},
            content_type="multipart/form-data",
        )
        assert missing_response.status_code == 400

        empty_response = client.post(
            f"/companies/{company.id}/cases/{case_id}/documents",
            headers=auth_header_for(user),
            data={
                "file": (BytesIO(b""), "empty.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )

        assert empty_response.status_code == 400


def test_upload_validation_mimetype_not_allowed_returns_400(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id, email="mimetype@example.com")
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, user.id)
        assign_role(db_session, user, "Operativo")
        assign_access(db_session, user, company, "operator")

        response = client.post(
            f"/companies/{company.id}/cases/{case_id}/documents",
            headers=auth_header_for(user),
            data={
                "file": (BytesIO(b"MZ executable"), "bad.pdf", "application/octet-stream"),
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 400


def test_update_document_status_creates_case_event(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id, email="status@example.com")
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, user.id)
        assign_role(db_session, user, "Operativo")
        assign_access(db_session, user, company, "operator")

        upload_response = client.post(
            f"/companies/{company.id}/cases/{case_id}/documents",
            headers=auth_header_for(user),
            data={
                "file": (BytesIO(b"%PDF-1.4 upload"), "status.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )
        assert upload_response.status_code == 201
        document_id = upload_response.get_json()["document"]["id"]

        response = client.patch(
            f"/documents/{document_id}/status",
            headers=auth_header_for(user),
            json={"status": "processed"},
        )

        assert response.status_code == 200
        payload = response.get_json()["document"]
        assert payload["status"] == "processed"

        events_response = client.get(
            f"/companies/{company.id}/cases/{case_id}/events",
            headers=auth_header_for(user),
        )
        assert events_response.status_code == 200
        assert any(
            event["event_type"] == "status_change"
            and event["payload"].get("document_id") == document_id
            and event["payload"].get("to") == "processed"
            for event in events_response.get_json().get("events", [])
        )


def test_list_documents_supports_has_extraction_filter(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id, email="extract@example.com")
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, user.id)
        assign_role(db_session, user, "Operativo")
        assign_access(db_session, user, company, "operator")

        service = DocumentModuleService()
        doc_with_extraction = service.upload_case_document(
            client_id=tenant.id,
            company_id=company.id,
            case_id=case_id,
            actor_user_id=user.id,
            file=FileStorage(
                stream=BytesIO(b"%PDF-1.4 with extraction"),
                filename="with-extraction.pdf",
                content_type="application/pdf",
            ),
        )
        service.upload_case_document(
            client_id=tenant.id,
            company_id=company.id,
            case_id=case_id,
            actor_user_id=user.id,
            file=FileStorage(
                stream=BytesIO(b"%PDF-1.4 without extraction"),
                filename="without-extraction.pdf",
                content_type="application/pdf",
            ),
        )
        db.session.add(
            DocumentExtraction(
                client_id=tenant.id,
                document_id=doc_with_extraction.id,
                company_id=company.id,
                case_id=case_id,
                created_by_user_id=user.id,
                provider="manual",
                schema_version="v1",
                extracted_json={"ok": True},
                status="success",
            )
        )
        db.session.commit()

        with_response = client.get(
            f"/companies/{company.id}/cases/{case_id}/documents?has_extraction=true",
            headers=auth_header_for(user),
        )
        assert with_response.status_code == 200
        with_items = with_response.get_json()["items"]
        assert len(with_items) == 1
        assert with_items[0]["has_extraction"] is True

        without_response = client.get(
            f"/companies/{company.id}/cases/{case_id}/documents?has_extraction=false",
            headers=auth_header_for(user),
        )
        assert without_response.status_code == 200
        without_items = without_response.get_json()["items"]
        assert len(without_items) == 1
        assert without_items[0]["has_extraction"] is False


def test_upload_document_with_person_id(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id)
        person = create_person(db_session, tenant.id, "p1")
        assign_role(db_session, user, "Operativo")

        response = client.post(
            "/documents",
            headers=auth_header_for(user),
            data={
                "person_id": person.id,
                "doc_type": "dni",
                "file": (BytesIO(b"%PDF-1.4 personal"), "dni.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 201
        assert response.get_json()["document"]["person_id"] == person.id


def test_upload_document_with_employee_infers_person(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id)
        company = create_company(db_session, tenant.id)
        person = create_person(db_session, tenant.id, "p2")
        employee = create_employee(db_session, tenant.id, company.id, person.id)
        assign_role(db_session, user, "Operativo")
        assign_access(db_session, user, company, "operator")

        response = client.post(
            "/documents",
            headers=auth_header_for(user),
            data={
                "employee_id": employee.id,
                "company_id": company.id,
                "doc_type": "payslip",
                "file": (BytesIO(b"%PDF-1.4 payslip"), "pay.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 201
        doc = response.get_json()["document"]
        assert doc["employee_id"] == employee.id
        assert doc["person_id"] == person.id


def test_upload_document_employee_person_mismatch_returns_400(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id)
        company = create_company(db_session, tenant.id)
        person_a = create_person(db_session, tenant.id, "pa")
        person_b = create_person(db_session, tenant.id, "pb")
        employee = create_employee(db_session, tenant.id, company.id, person_a.id)
        assign_role(db_session, user, "Operativo")
        assign_access(db_session, user, company, "operator")

        response = client.post(
            "/documents",
            headers=auth_header_for(user),
            data={
                "company_id": company.id,
                "employee_id": employee.id,
                "person_id": person_b.id,
                "file": (BytesIO(b"%PDF-1.4 bad"), "bad.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 400


def test_upload_document_employee_company_mismatch_returns_400(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id)
        company_a = create_company(db_session, tenant.id, name="A", tax_id="TA")
        company_b = create_company(db_session, tenant.id, name="B", tax_id="TB")
        employee = create_employee(db_session, tenant.id, company_a.id, None)
        assign_role(db_session, user, "Operativo")
        assign_access(db_session, user, company_a, "operator")
        assign_access(db_session, user, company_b, "operator")

        response = client.post(
            "/documents",
            headers=auth_header_for(user),
            data={
                "company_id": company_b.id,
                "employee_id": employee.id,
                "file": (BytesIO(b"%PDF-1.4 bad"), "bad2.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )

        assert response.status_code == 400


def test_list_documents_by_person_and_employee(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id)
        company = create_company(db_session, tenant.id)
        person = create_person(db_session, tenant.id, "pf")
        employee = create_employee(db_session, tenant.id, company.id, person.id)
        assign_role(db_session, user, "Operativo")
        assign_access(db_session, user, company, "operator")

        upload = lambda **data: client.post(
            "/documents",
            headers=auth_header_for(user),
            data={**data, "file": (BytesIO(b"%PDF-1.4 ok"), f"{uuid4()}.pdf", "application/pdf")},
            content_type="multipart/form-data",
        )

        upload(company_id=company.id, person_id=person.id, doc_type="personal_document")
        upload(company_id=company.id, employee_id=employee.id, doc_type="payslip")

        by_person = client.get(f"/documents?person_id={person.id}", headers=auth_header_for(user))
        assert by_person.status_code == 200
        assert len(by_person.get_json()["items"]) >= 2

        by_employee = client.get(f"/documents?employee_id={employee.id}", headers=auth_header_for(user))
        assert by_employee.status_code == 200
        assert len(by_employee.get_json()["items"]) == 1


def test_documents_listing_keeps_tenant_isolation(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant_a = create_client(db_session)
        tenant_b = create_client(db_session)
        seed_rbac()
        user_a = create_user(db_session, tenant_a.id, email="a@a.com")
        user_b = create_user(db_session, tenant_b.id, email="b@b.com")
        assign_role(db_session, user_a, "Operativo")
        assign_role(db_session, user_b, "Operativo")

        person_a = create_person(db_session, tenant_a.id, "ta")
        client.post(
            "/documents",
            headers=auth_header_for(user_a),
            data={
                "person_id": person_a.id,
                "doc_type": "personal_document",
                "file": (BytesIO(b"%PDF-1.4 secret"), "secret.pdf", "application/pdf"),
            },
            content_type="multipart/form-data",
        )

        response = client.get(f"/documents?person_id={person_a.id}", headers=auth_header_for(user_b))
        assert response.status_code == 200
        assert response.get_json()["total"] == 0
