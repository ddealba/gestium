from uuid import uuid4

import pytest
from werkzeug.exceptions import BadRequest, NotFound

from app.extensions import db
from app.models.case import Case
from app.models.client import Client
from app.models.company import Company
from app.models.document import Document
from app.models.user import User
from app.modules.extractions.service import DocumentExtractionService


@pytest.fixture()
def db_session(app):
    with app.app_context():
        db.create_all()
        yield db.session
        db.session.remove()
        db.drop_all()


def _create_client(db_session: db.Session, name: str | None = None) -> Client:
    client = Client(name=name or f"Tenant-{uuid4()}")
    db_session.add(client)
    db_session.commit()
    return client


def _create_user(db_session: db.Session, client_id: str) -> User:
    user = User(client_id=client_id, email=f"user-{uuid4()}@example.com", status="active")
    db_session.add(user)
    db_session.commit()
    return user


def _create_document(db_session: db.Session, client_id: str) -> Document:
    company = Company(client_id=client_id, name=f"Co-{uuid4()}", tax_id=f"TAX-{uuid4()}")
    db_session.add(company)
    db_session.flush()

    case = Case(client_id=client_id, company_id=company.id, title="Case", type="general", status="open")
    db_session.add(case)
    db_session.flush()

    document = Document(
        client_id=client_id,
        company_id=company.id,
        case_id=case.id,
        original_filename="doc.pdf",
        content_type="application/pdf",
        storage_path="dummy/doc.pdf",
        size_bytes=100,
        status="pending",
    )
    db_session.add(document)
    db_session.commit()
    return document


def test_create_extraction_sets_denormalized_fields_and_can_be_queried(app, db_session):
    with app.app_context():
        tenant = _create_client(db_session)
        user = _create_user(db_session, tenant.id)
        document = _create_document(db_session, tenant.id)

        service = DocumentExtractionService()
        created = service.create_extraction(
            client_id=tenant.id,
            actor_user_id=user.id,
            document=document,
            schema_version="v1",
            extracted_json={"field": "value"},
            confidence=0.95,
        )
        db.session.commit()

        assert created.client_id == tenant.id
        assert created.document_id == document.id
        assert created.company_id == document.company_id
        assert created.case_id == document.case_id

        fetched = service.get_extraction(created.id, tenant.id)
        assert fetched.id == created.id

        listed = service.list_extractions(document.id, tenant.id)
        assert [item.id for item in listed] == [created.id]

        latest = service.get_latest(document.id, tenant.id)
        assert latest is not None
        assert latest.id == created.id


def test_create_extraction_rejects_non_tenant_document(app, db_session):
    with app.app_context():
        tenant_a = _create_client(db_session, name=f"TenantA-{uuid4()}")
        tenant_b = _create_client(db_session, name=f"TenantB-{uuid4()}")
        user = _create_user(db_session, tenant_a.id)
        document_other_tenant = _create_document(db_session, tenant_b.id)

        service = DocumentExtractionService()
        with pytest.raises(NotFound, match="document_not_found"):
            service.create_extraction(
                client_id=tenant_a.id,
                actor_user_id=user.id,
                document=document_other_tenant,
                schema_version="v1",
                extracted_json={"field": "value"},
            )


def test_create_extraction_requires_schema_version(app, db_session):
    with app.app_context():
        tenant = _create_client(db_session)
        user = _create_user(db_session, tenant.id)
        document = _create_document(db_session, tenant.id)

        service = DocumentExtractionService()
        with pytest.raises(BadRequest, match="schema_version_required"):
            service.create_extraction(
                client_id=tenant.id,
                actor_user_id=user.id,
                document=document,
                schema_version=" ",
                extracted_json={"field": "value"},
            )


def test_create_extraction_validates_confidence_range(app, db_session):
    with app.app_context():
        tenant = _create_client(db_session)
        user = _create_user(db_session, tenant.id)
        document = _create_document(db_session, tenant.id)

        service = DocumentExtractionService()
        with pytest.raises(BadRequest, match="confidence_out_of_range"):
            service.create_extraction(
                client_id=tenant.id,
                actor_user_id=user.id,
                document=document,
                schema_version="v1",
                extracted_json={"field": "value"},
                confidence=1.1,
            )


def test_get_extraction_not_found_for_other_tenant(app, db_session):
    with app.app_context():
        tenant_a = _create_client(db_session, name=f"TenantA-{uuid4()}")
        tenant_b = _create_client(db_session, name=f"TenantB-{uuid4()}")
        user = _create_user(db_session, tenant_a.id)
        document = _create_document(db_session, tenant_a.id)

        service = DocumentExtractionService()
        extraction = service.create_extraction(
            client_id=tenant_a.id,
            actor_user_id=user.id,
            document=document,
            schema_version="v1",
            extracted_json={"field": "value"},
        )
        db.session.commit()

        with pytest.raises(NotFound, match="extraction_not_found"):
            service.get_extraction(extraction.id, tenant_b.id)
