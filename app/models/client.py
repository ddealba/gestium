"""Client (tenant) model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class Client(BaseModel):
    """Represents a tenant in the system."""

    __tablename__ = "clients"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False, unique=True, index=True)
    status = db.Column(
        db.Enum("active", "suspended", "disabled", name="client_status"),
        nullable=False,
        index=True,
        default="active",
    )
    plan = db.Column(db.String(100), nullable=True)

    def __repr__(self) -> str:
        return f"<Client id={self.id} name={self.name} status={self.status}>"
