"""Document extraction model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db


class DocumentExtraction(db.Model):
    """Structured extraction results associated with a document."""

    __tablename__ = "document_extractions"
    __table_args__ = (
        db.Index(
            "ix_document_extractions_client_document_created_at",
            "client_id",
            "document_id",
            "created_at",
        ),
        db.Index(
            "ix_document_extractions_client_company_created_at",
            "client_id",
            "company_id",
            "created_at",
        ),
        db.Index("ix_document_extractions_client_status", "client_id", "status"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    document_id = db.Column(db.String(36), db.ForeignKey("documents.id"), nullable=False, index=True)
    company_id = db.Column(db.String(36), db.ForeignKey("companies.id"), nullable=False, index=True)
    case_id = db.Column(db.String(36), db.ForeignKey("cases.id"), nullable=True, index=True)
    created_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True, index=True)

    provider = db.Column(db.String(100), nullable=True)
    model_name = db.Column(db.String(255), nullable=True)
    schema_version = db.Column(db.String(50), nullable=False)
    extracted_json = db.Column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    confidence = db.Column(db.Float, nullable=True)
    status = db.Column(
        db.Enum("success", "failed", "partial", name="document_extraction_status"),
        nullable=False,
        index=True,
    )
    error_message = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    client = db.relationship("Client", backref=db.backref("document_extractions", lazy="dynamic"))
    document = db.relationship("Document", backref=db.backref("extractions", lazy="dynamic"))
    company = db.relationship("Company", backref=db.backref("document_extractions", lazy="dynamic"))
    case = db.relationship("Case", backref=db.backref("document_extractions", lazy="dynamic"))
    created_by_user = db.relationship("User", backref=db.backref("created_extractions", lazy="dynamic"))

    def __repr__(self) -> str:
        return (
            "<DocumentExtraction id={id} client_id={client_id} document_id={document_id} "
            "status={status} schema_version={schema_version}>"
        ).format(
            id=self.id,
            client_id=self.client_id,
            document_id=self.document_id,
            status=self.status,
            schema_version=self.schema_version,
        )
