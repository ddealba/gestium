from __future__ import annotations

from io import BytesIO

from app.models.user import User
from app.repositories.user_role_repository import UserRoleRepository


def _upload_pdf(client, *, company_id: str, case_id: str, headers: dict[str, str]):
    return client.post(
        f"/companies/{company_id}/cases/{case_id}/documents",
        headers=headers,
        data={
            "doc_type": "evidence",
            "file": (BytesIO(b"%PDF-1.4 test"), "evidence.pdf", "application/pdf"),
        },
        content_type="multipart/form-data",
    )


def test_cross_tenant_list_documents_returns_404(client, app, document_scenario, login, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        admin_a_headers = login("admina@test.com", "Passw0rd!", document_scenario.client_a_id)
        admin_b_headers = login("adminb@test.com", "Passw0rd!", document_scenario.client_b_id)

        upload_response = _upload_pdf(
            client,
            company_id=document_scenario.company_a_id,
            case_id=document_scenario.case_a_id,
            headers=admin_a_headers,
        )
        assert upload_response.status_code == 201

        response = client.get(
            f"/companies/{document_scenario.company_a_id}/cases/{document_scenario.case_a_id}/documents",
            headers=admin_b_headers,
        )

        assert response.status_code == 404


def test_cross_tenant_download_document_returns_404(client, app, document_scenario, login, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        admin_a_headers = login("admina@test.com", "Passw0rd!", document_scenario.client_a_id)
        admin_b_headers = login("adminb@test.com", "Passw0rd!", document_scenario.client_b_id)

        upload_response = _upload_pdf(
            client,
            company_id=document_scenario.company_a_id,
            case_id=document_scenario.case_a_id,
            headers=admin_a_headers,
        )
        document_id = upload_response.get_json()["document"]["id"]

        response = client.get(f"/documents/{document_id}/download", headers=admin_b_headers)

        assert response.status_code == 404


def test_acl_list_without_company_access_returns_404(client, app, document_scenario, login, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        admin_a_headers = login("admina@test.com", "Passw0rd!", document_scenario.client_a_id)
        no_acl_headers = login("noacla@test.com", "Passw0rd!", document_scenario.client_a_id)

        upload_response = _upload_pdf(
            client,
            company_id=document_scenario.company_a_id,
            case_id=document_scenario.case_a_id,
            headers=admin_a_headers,
        )
        assert upload_response.status_code == 201

        response = client.get(
            f"/companies/{document_scenario.company_a_id}/cases/{document_scenario.case_a_id}/documents",
            headers=no_acl_headers,
        )

        assert response.status_code == 403


def test_acl_download_without_company_access_returns_404(client, app, document_scenario, login, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        admin_a_headers = login("admina@test.com", "Passw0rd!", document_scenario.client_a_id)
        no_acl_headers = login("noacla@test.com", "Passw0rd!", document_scenario.client_a_id)

        upload_response = _upload_pdf(
            client,
            company_id=document_scenario.company_a_id,
            case_id=document_scenario.case_a_id,
            headers=admin_a_headers,
        )
        document_id = upload_response.get_json()["document"]["id"]

        response = client.get(f"/documents/{document_id}/download", headers=no_acl_headers)

        assert response.status_code == 403


def test_rbac_without_document_read_returns_403(client, app, document_scenario, login, role_without_permission_factory, db_session):
    with app.app_context():
        role = role_without_permission_factory(
            client_id=document_scenario.client_a_id,
            name="ViewerNoDocRead",
            allowed_permission_codes=["case.read"],
        )
        user = User.query.filter_by(id=document_scenario.user_viewer_a_id).one()
        user.roles = [role]
        db_session.commit()

        viewer_headers = login("viewera@test.com", "Passw0rd!", document_scenario.client_a_id)

        response = client.get(
            f"/companies/{document_scenario.company_a_id}/cases/{document_scenario.case_a_id}/documents",
            headers=viewer_headers,
        )

        assert response.status_code == 403


def test_rbac_without_document_upload_returns_403(client, app, document_scenario, login, role_without_permission_factory, db_session):
    with app.app_context():
        role = role_without_permission_factory(
            client_id=document_scenario.client_a_id,
            name="OperatorNoDocUpload",
            allowed_permission_codes=["document.read", "case.read"],
        )
        UserRoleRepository(db_session).assign_role(document_scenario.user_viewer_a_id, role.id)
        db_session.commit()

        viewer_headers = login("viewera@test.com", "Passw0rd!", document_scenario.client_a_id)

        response = _upload_pdf(
            client,
            company_id=document_scenario.company_a_id,
            case_id=document_scenario.case_a_id,
            headers=viewer_headers,
        )

        assert response.status_code == 403
