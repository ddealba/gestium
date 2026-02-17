"""Document model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class Document(BaseModel):
    """Represents a document belonging to a company/case."""

    __tablename__ = "documents"
    __table_args__ = (
        db.Index("ix_documents_client_company_case", "client_id", "company_id", "case_id"),
        db.Index("ix_documents_client_status", "client_id", "status"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    company_id = db.Column(db.String(36), db.ForeignKey("companies.id"), nullable=False, index=True)
    case_id = db.Column(db.String(36), db.ForeignKey("cases.id"), nullable=False, index=True)
    uploaded_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True, index=True)

    original_filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(255), nullable=True)
    storage_path = db.Column(db.String(512), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=True)
    doc_type = db.Column(db.String(100), nullable=True)
    status = db.Column(
        db.Enum("pending", "processed", "archived", name="document_status"),
        nullable=False,
        index=True,
        default="pending",
    )

    company = db.relationship("Company", backref=db.backref("documents", lazy="dynamic"))
    case = db.relationship("Case", backref=db.backref("documents", lazy="dynamic"))
    uploaded_by_user = db.relationship("User", backref=db.backref("uploaded_documents", lazy="dynamic"))

    def __repr__(self) -> str:
        return (
            "<Document id={id} client_id={client_id} company_id={company_id} "
            "case_id={case_id} status={status} original_filename={original_filename}>"
        ).format(
            id=self.id,
            client_id=self.client_id,
            company_id=self.company_id,
            case_id=self.case_id,
            status=self.status,
            original_filename=self.original_filename,
        )
