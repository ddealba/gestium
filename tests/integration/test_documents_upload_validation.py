from __future__ import annotations

from io import BytesIO
from pathlib import Path

from app.models.document import Document


def _upload(client, *, company_id: str, case_id: str, headers: dict[str, str], data: dict):
    return client.post(
        f"/companies/{company_id}/cases/{case_id}/documents",
        headers=headers,
        data=data,
        content_type="multipart/form-data",
    )


def test_upload_missing_file_returns_400(client, app, document_scenario, login, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        admin_headers = login("admina@test.com", "Passw0rd!", document_scenario.client_a_id)

        response = _upload(
            client,
            company_id=document_scenario.company_a_id,
            case_id=document_scenario.case_a_id,
            headers=admin_headers,
            data={"doc_type": "evidence"},
        )

        assert response.status_code == 400
        assert response.get_json()["message"] == "file_required"


def test_upload_mimetype_not_allowed_returns_400(client, app, document_scenario, login, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)
        admin_headers = login("admina@test.com", "Passw0rd!", document_scenario.client_a_id)

        response = _upload(
            client,
            company_id=document_scenario.company_a_id,
            case_id=document_scenario.case_a_id,
            headers=admin_headers,
            data={
                "file": (BytesIO(b"MZ binary"), "evil.pdf", "application/x-msdownload"),
            },
        )

        assert response.status_code == 400
        assert response.get_json()["message"] == "mimetype_not_allowed"


def test_upload_file_too_large_is_controlled_error(client, app, document_scenario, login, tmp_path):
    with app.app_context():
        admin_headers = login("admina@test.com", "Passw0rd!", document_scenario.client_a_id)
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)
        app.config["MAX_CONTENT_LENGTH"] = 16

        response = _upload(
            client,
            company_id=document_scenario.company_a_id,
            case_id=document_scenario.case_a_id,
            headers=admin_headers,
            data={
                "file": (BytesIO(b"%PDF-1.4 this payload is larger than 16 bytes"), "big.pdf", "application/pdf"),
            },
        )

        assert response.status_code in (400, 413)
        assert response.is_json


def test_upload_filename_traversal_is_sanitized(client, app, db_session, document_scenario, login, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)
        admin_headers = login("admina@test.com", "Passw0rd!", document_scenario.client_a_id)

        response = _upload(
            client,
            company_id=document_scenario.company_a_id,
            case_id=document_scenario.case_a_id,
            headers=admin_headers,
            data={
                "file": (BytesIO(b"%PDF-1.4 safe"), "../evil.pdf", "application/pdf"),
            },
        )

        assert response.status_code == 201
        document_id = response.get_json()["document"]["id"]

        stored = Document.query.filter_by(id=document_id, client_id=document_scenario.client_a_id).one()
        assert ".." not in stored.original_filename

        root = Path(app.config["DOCUMENT_STORAGE_ROOT"]).resolve()
        full_path = (root / stored.storage_path).resolve()
        assert root in full_path.parents
        assert full_path.exists()
