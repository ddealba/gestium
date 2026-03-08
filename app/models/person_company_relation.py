"""Person-company relation model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class PersonCompanyRelation(BaseModel):
    """Represents a tenant-scoped relation between a person and a company."""

    __tablename__ = "person_company_relations"
    __table_args__ = (
        db.Index("ix_pcr_client_id", "client_id"),
        db.Index("ix_pcr_person_id", "person_id"),
        db.Index("ix_pcr_company_id", "company_id"),
        db.Index("ix_pcr_relation_type", "relation_type"),
        db.Index("ix_pcr_status", "status"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False)
    person_id = db.Column(db.String(36), db.ForeignKey("persons.id"), nullable=False)
    company_id = db.Column(db.String(36), db.ForeignKey("companies.id"), nullable=False)
    relation_type = db.Column(
        db.Enum("owner", "employee", "other", name="person_company_relation_type"),
        nullable=False,
    )
    status = db.Column(
        db.Enum("active", "inactive", name="person_company_relation_status"),
        nullable=False,
        default="active",
    )
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)

    person = db.relationship("Person", backref=db.backref("company_relations", lazy="dynamic"))
    company = db.relationship("Company", backref=db.backref("person_relations", lazy="dynamic"))
    creator = db.relationship("User", backref=db.backref("created_person_company_relations", lazy="dynamic"))
