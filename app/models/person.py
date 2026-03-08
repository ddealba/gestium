"""Person model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class Person(BaseModel):
    """Represents a natural person within a tenant."""

    __tablename__ = "persons"
    __table_args__ = (
        db.UniqueConstraint("client_id", "email", name="uq_persons_client_email"),
        db.Index("ix_persons_client_document", "client_id", "document_number"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    first_name = db.Column(db.String(120), nullable=False)
    last_name = db.Column(db.String(120), nullable=False)
    document_type = db.Column(db.String(50), nullable=True)
    document_number = db.Column(db.String(100), nullable=False, index=True)
    email = db.Column(db.String(255), nullable=True, index=True)
    phone = db.Column(db.String(50), nullable=True)
    birth_date = db.Column(db.Date, nullable=True)
    address_line1 = db.Column(db.String(255), nullable=True)
    address_line2 = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(120), nullable=True)
    postal_code = db.Column(db.String(30), nullable=True)
    country = db.Column(db.String(120), nullable=True)
    status = db.Column(
        db.Enum("draft", "pending_info", "active", "inactive", name="person_status"),
        nullable=False,
        index=True,
        default="draft",
    )
    created_by = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True, index=True)

    client = db.relationship("Client", backref=db.backref("persons", lazy="dynamic"))
    creator = db.relationship("User", backref=db.backref("created_persons", lazy="dynamic"))

    def __repr__(self) -> str:
        return (
            "<Person id={id} client_id={client_id} name={name} document_number={document_number} status={status}>"
        ).format(
            id=self.id,
            client_id=self.client_id,
            name=f"{self.first_name} {self.last_name}",
            document_number=self.document_number,
            status=self.status,
        )
