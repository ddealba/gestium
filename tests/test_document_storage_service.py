from io import BytesIO
from uuid import uuid4

import pytest
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest

from app.extensions import db
from app.models.case_event import CaseEvent
from app.models.client import Client
from app.models.company import Company
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.models.user import User
from app.modules.cases.service import CaseService
from app.modules.documents.service import DocumentModuleService


def _create_client() -> Client:
    client = Client(name=f"Acme-{uuid4()}")
    db.session.add(client)
    db.session.commit()
    return client


def _create_company(client_id: str) -> Company:
    company = Company(client_id=client_id, name="Alpha", tax_id="A-123")
    db.session.add(company)
    db.session.commit()
    return company


def _create_user(client_id: str, email: str) -> User:
    user = User(client_id=client_id, email=email, status="active")
    db.session.add(user)
    db.session.commit()
    return user


def test_upload_case_document_saves_file_and_creates_attachment_event(app, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf", "png", "jpg")

        db.create_all()
        tenant = _create_client()
        company = _create_company(tenant.id)
        actor = _create_user(tenant.id, "owner@example.com")
        case = CaseService().create_case(
            client_id=tenant.id,
            company_id=company.id,
            actor_user_id=actor.id,
            payload={"title": "Caso con adjuntos"},
        )

        file = FileStorage(
            stream=BytesIO(b"%PDF-1.4 fake content"),
            filename="evidencia.pdf",
            content_type="application/pdf",
        )

        document = DocumentModuleService().upload_case_document(
            client_id=tenant.id,
            company_id=company.id,
            case_id=case.id,
            actor_user_id=actor.id,
            file=file,
            doc_type="evidence",
        )
        db.session.commit()

        stored_document = db.session.query(Document).filter(Document.id == document.id).one()
        assert stored_document.status == "pending"
        stored_path = tmp_path / stored_document.storage_path
        assert stored_path.exists()
        assert str(stored_path).startswith(str(tmp_path / tenant.id / company.id / case.id))

        attachment_event = (
            db.session.query(CaseEvent)
            .filter(CaseEvent.case_id == case.id, CaseEvent.event_type == "attachment")
            .one()
        )
        assert attachment_event.payload["document_id"] == document.id
        assert attachment_event.payload["filename"] == "evidencia.pdf"



def test_upload_case_document_creates_placeholder_extraction_when_enabled(app, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf", "png", "jpg")
        app.config["AUTO_EXTRACTION_ENABLED"] = True

        db.create_all()
        tenant = _create_client()
        company = _create_company(tenant.id)
        actor = _create_user(tenant.id, "owner@example.com")
        case = CaseService().create_case(
            client_id=tenant.id,
            company_id=company.id,
            actor_user_id=actor.id,
            payload={"title": "Caso con extracción automática"},
        )

        file = FileStorage(
            stream=BytesIO(b"%PDF-1.4 fake content"),
            filename="autoevidencia.pdf",
            content_type="application/pdf",
        )

        document = DocumentModuleService().upload_case_document(
            client_id=tenant.id,
            company_id=company.id,
            case_id=case.id,
            actor_user_id=actor.id,
            file=file,
            doc_type="evidence",
        )
        db.session.commit()

        extraction = (
            db.session.query(DocumentExtraction)
            .filter(DocumentExtraction.document_id == document.id)
            .one()
        )
        assert extraction.status == "partial"
        assert extraction.provider == "system"
        assert extraction.extracted_json == {}



def test_upload_case_document_validates_size_and_extension(app, tmp_path):
    with app.app_context():
        app.config["DOCUMENT_STORAGE_ROOT"] = str(tmp_path)
        app.config["MAX_CONTENT_LENGTH"] = 3
        app.config["ALLOWED_DOCUMENT_MIME"] = ("pdf",)

        db.create_all()
        tenant = _create_client()
        company = _create_company(tenant.id)
        actor = _create_user(tenant.id, "owner@example.com")
        case = CaseService().create_case(
            client_id=tenant.id,
            company_id=company.id,
            actor_user_id=actor.id,
            payload={"title": "Caso con validaciones"},
        )

        service = DocumentModuleService()
        with pytest.raises(BadRequest) as ext_error:
            service.upload_case_document(
                client_id=tenant.id,
                company_id=company.id,
                case_id=case.id,
                actor_user_id=actor.id,
                file=FileStorage(
                    stream=BytesIO(b"hello"),
                    filename="evidencia.exe",
                    content_type="application/octet-stream",
                ),
            )
        assert ext_error.value.description == "extension_not_allowed"

        with pytest.raises(BadRequest) as size_error:
            service.upload_case_document(
                client_id=tenant.id,
                company_id=company.id,
                case_id=case.id,
                actor_user_id=actor.id,
                file=FileStorage(
                    stream=BytesIO(b"12345"),
                    filename="evidencia.pdf",
                    content_type="application/pdf",
                ),
            )
        assert size_error.value.description == "file_too_large"
