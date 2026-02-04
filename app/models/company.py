"""Company model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class Company(BaseModel):
    """Represents a company within a tenant."""

    __tablename__ = "companies"
    __table_args__ = (
        db.UniqueConstraint("client_id", "tax_id", name="uq_companies_client_tax_id"),
        db.Index("ix_companies_client_status", "client_id", "status"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    tax_id = db.Column(db.String(50), nullable=False, index=True)
    status = db.Column(
        db.Enum("active", "inactive", name="company_status"),
        nullable=False,
        index=True,
        default="active",
    )

    client = db.relationship("Client", backref=db.backref("companies", lazy="dynamic"))

    def __repr__(self) -> str:
        return (
            "<Company id={id} client_id={client_id} name={name} tax_id={tax_id} status={status}>"
        ).format(
            id=self.id,
            client_id=self.client_id,
            name=self.name,
            tax_id=self.tax_id,
            status=self.status,
        )
