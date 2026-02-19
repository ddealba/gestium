from io import BytesIO
from uuid import uuid4

from werkzeug.datastructures import FileStorage

from app.cli import seed_rbac
from app.common.jwt import create_access_token
from app.extensions import db
from app.models.client import Client
from app.models.company import Company
from app.models.role import Role
from app.models.user import User
from app.modules.cases.service import CaseService
from app.modules.documents.service import DocumentModuleService
from app.modules.extractions.service import DocumentExtractionService
from app.repositories.user_company_access_repository import UserCompanyAccessRepository
from app.repositories.user_role_repository import UserRoleRepository


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


def create_case(tenant_id: str, company_id: str, actor_user_id: str) -> str:
    case = CaseService().create_case(
        client_id=tenant_id,
        company_id=company_id,
        actor_user_id=actor_user_id,
        payload={"title": "Caso extracción"},
    )
    db.session.commit()
    return case.id


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


def upload_document(tenant, company, case_id, user) -> str:
    document = DocumentModuleService().upload_case_document(
        client_id=tenant.id,
        company_id=company.id,
        case_id=case_id,
        actor_user_id=user.id,
        file=FileStorage(
            stream=BytesIO(b"%PDF-1.4 sample"),
            filename="sample.pdf",
            content_type="application/pdf",
        ),
    )
    db.session.commit()
    return document.id


def test_create_extraction_latest_and_list(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id)
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, user.id)
        assign_role(db_session, user, "Admin Cliente")
        assign_access(db_session, user, company, "operator")
        document_id = upload_document(tenant, company, case_id, user)

        response = client.post(
            f"/documents/{document_id}/extractions",
            headers=auth_header_for(user),
            json={
                "schema_version": "v1",
                "extracted_json": {"invoice_number": "INV-001"},
                "confidence": 0.82,
                "provider": "manual",
                "model_name": None,
                "status": "success",
                "error_message": None,
            },
        )

        assert response.status_code == 201
        extraction = response.get_json()["extraction"]
        assert extraction["document_id"] == document_id
        assert extraction["schema_version"] == "v1"

        latest_response = client.get(
            f"/documents/{document_id}/extractions/latest",
            headers=auth_header_for(user),
        )
        assert latest_response.status_code == 200
        assert latest_response.get_json()["extraction"]["id"] == extraction["id"]

        list_response = client.get(
            f"/documents/{document_id}/extractions?limit=10&offset=0",
            headers=auth_header_for(user),
        )
        assert list_response.status_code == 200
        payload = list_response.get_json()
        assert payload["count"] == 1
        assert payload["items"][0]["id"] == extraction["id"]


def test_extraction_read_without_company_access_returns_404(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        uploader = create_user(db_session, tenant.id, email="uploader@example.com")
        reader = create_user(db_session, tenant.id, email="reader@example.com")
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, uploader.id)
        assign_role(db_session, uploader, "Admin Cliente")
        assign_access(db_session, uploader, company, "operator")
        assign_role(db_session, reader, "Asesor")

        document_id = upload_document(tenant, company, case_id, uploader)
        document = DocumentModuleService().document_repository.get_by_id(tenant.id, document_id)
        DocumentExtractionService().create_extraction(
            client_id=tenant.id,
            actor_user_id=uploader.id,
            document=document,
            schema_version="v1",
            extracted_json={"k": "v"},
        )
        db.session.commit()

        response = client.get(
            f"/documents/{document_id}/extractions/latest",
            headers=auth_header_for(reader),
        )
        assert response.status_code == 404
        assert response.get_json()["message"] == "document_not_found"


def test_create_extraction_invalid_status_returns_400(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id)
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, user.id)
        assign_role(db_session, user, "Admin Cliente")
        assign_access(db_session, user, company, "operator")
        document_id = upload_document(tenant, company, case_id, user)

        response = client.post(
            f"/documents/{document_id}/extractions",
            headers=auth_header_for(user),
            json={
                "schema_version": "v1",
                "extracted_json": {"invoice_number": "INV-001"},
                "status": "unknown",
            },
        )

        assert response.status_code == 400
        assert response.get_json()["message"] == "invalid_status"


def test_extraction_happy_path_and_cross_tenant_isolation(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant_a = create_client(db_session)
        tenant_b = create_client(db_session)
        seed_rbac()

        admin_a = create_user(db_session, tenant_a.id, email="admin-a@example.com")
        operator_a = create_user(db_session, tenant_a.id, email="operator-a@example.com")
        admin_b = create_user(db_session, tenant_b.id, email="admin-b@example.com")

        company_a = create_company(db_session, tenant_a.id, name="Company A", tax_id="A-001")
        case_id_a = create_case(tenant_a.id, company_a.id, admin_a.id)

        assign_role(db_session, admin_a, "Admin Cliente")
        assign_role(db_session, operator_a, "Operativo")
        assign_role(db_session, admin_b, "Admin Cliente")

        assign_access(db_session, admin_a, company_a, "admin")
        assign_access(db_session, operator_a, company_a, "operator")

        document_id = upload_document(tenant_a, company_a, case_id_a, admin_a)

        create_payload = {
            "schema_version": "v1",
            "extracted_json": {"invoice_number": "INV-001", "total": 123.45},
            "confidence": 0.91,
            "provider": "manual",
            "model_name": "qa-model",
            "status": "success",
        }

        create_response = client.post(
            f"/documents/{document_id}/extractions",
            headers=auth_header_for(admin_a),
            json=create_payload,
        )
        assert create_response.status_code == 201

        latest_response = client.get(
            f"/documents/{document_id}/extractions/latest",
            headers=auth_header_for(admin_a),
        )
        assert latest_response.status_code == 200

        extraction = latest_response.get_json()["extraction"]
        assert extraction["document_id"] == document_id
        assert extraction["schema_version"] == create_payload["schema_version"]
        assert extraction["extracted_json"] == create_payload["extracted_json"]
        assert extraction["confidence"] == create_payload["confidence"]
        assert extraction["provider"] == create_payload["provider"]
        assert extraction["model_name"] == create_payload["model_name"]
        assert extraction["status"] == create_payload["status"]

        cross_tenant_get = client.get(
            f"/documents/{document_id}/extractions/latest",
            headers=auth_header_for(admin_b),
        )
        assert cross_tenant_get.status_code == 404
        assert cross_tenant_get.get_json()["message"] == "document_not_found"

        cross_tenant_post = client.post(
            f"/documents/{document_id}/extractions",
            headers=auth_header_for(admin_b),
            json=create_payload,
        )
        assert cross_tenant_post.status_code == 404
        assert cross_tenant_post.get_json()["message"] == "document_not_found"


def test_extraction_endpoints_enforce_rbac_permissions(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()

        admin_user = create_user(db_session, tenant.id, email="admin@example.com")
        limited_user = create_user(db_session, tenant.id, email="limited@example.com")
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, admin_user.id)

        assign_role(db_session, admin_user, "Admin Cliente")
        assign_role(db_session, limited_user, "Operativo")
        assign_access(db_session, admin_user, company, "admin")
        assign_access(db_session, limited_user, company, "operator")

        document_id = upload_document(tenant, company, case_id, admin_user)

        post_response = client.post(
            f"/documents/{document_id}/extractions",
            headers=auth_header_for(limited_user),
            json={"schema_version": "v1", "extracted_json": {"foo": "bar"}},
        )
        assert post_response.status_code == 403
        assert post_response.get_json()["message"] == "missing_permission"

        document = DocumentModuleService().document_repository.get_by_id(tenant.id, document_id)
        DocumentExtractionService().create_extraction(
            client_id=tenant.id,
            actor_user_id=admin_user.id,
            document=document,
            schema_version="v1",
            extracted_json={"foo": "bar"},
        )
        db.session.commit()

        get_response = client.get(
            f"/documents/{document_id}/extractions/latest",
            headers=auth_header_for(limited_user),
        )
        assert get_response.status_code == 403
        assert get_response.get_json()["message"] == "missing_permission"


def test_create_extraction_payload_validations(client, app, db_session, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        tenant = create_client(db_session)
        seed_rbac()
        user = create_user(db_session, tenant.id)
        company = create_company(db_session, tenant.id)
        case_id = create_case(tenant.id, company.id, user.id)

        assign_role(db_session, user, "Admin Cliente")
        assign_access(db_session, user, company, "operator")

        document_id = upload_document(tenant, company, case_id, user)

        confidence_out_of_range_response = client.post(
            f"/documents/{document_id}/extractions",
            headers=auth_header_for(user),
            json={
                "schema_version": "v1",
                "extracted_json": {"invoice_number": "INV-123"},
                "confidence": 1.2,
            },
        )
        assert confidence_out_of_range_response.status_code == 400
        assert confidence_out_of_range_response.get_json()["message"] == "confidence_out_of_range"

        missing_schema_version_response = client.post(
            f"/documents/{document_id}/extractions",
            headers=auth_header_for(user),
            json={
                "extracted_json": {"invoice_number": "INV-123"},
                "confidence": 0.8,
            },
        )
        assert missing_schema_version_response.status_code == 400
        assert missing_schema_version_response.get_json()["message"] == "schema_version_required"
