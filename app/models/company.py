"""Company model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class Company(BaseModel):
    """Represents a company within a tenant."""

    __tablename__ = "companies"
    __table_args__ = (
        db.UniqueConstraint("client_id", "name", name="uq_companies_client_name"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)

    client = db.relationship("Client", backref=db.backref("companies", lazy="dynamic"))

    def __repr__(self) -> str:
        return f"<Company id={self.id} client_id={self.client_id} name={self.name}>"
