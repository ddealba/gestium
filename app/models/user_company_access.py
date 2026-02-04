"""User-company access model for tenant-scoped ACLs."""

from __future__ import annotations

import uuid

from app.common.access_levels import AccessLevel
from app.extensions import db
from app.models.base import BaseModel


class UserCompanyAccess(BaseModel):
    """Access levels for users scoped to companies within a tenant."""

    __tablename__ = "user_company_access"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "company_id",
            name="uq_user_company_access_user_company",
        ),
    )

    # Use a surrogate UUID primary key to make updates easy while keeping uniqueness
    # enforced via (user_id, company_id) constraint.
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    company_id = db.Column(db.String(36), nullable=False, index=True)
    access_level = db.Column(
        db.Enum(*[level.value for level in AccessLevel], name="company_access_level"),
        nullable=False,
        index=True,
    )

    user = db.relationship("User", backref=db.backref("company_access", lazy="dynamic"))

    def __repr__(self) -> str:
        return (
            "<UserCompanyAccess id={id} client_id={client_id} user_id={user_id} "
            "company_id={company_id} access_level={access_level}>"
        ).format(
            id=self.id,
            client_id=self.client_id,
            user_id=self.user_id,
            company_id=self.company_id,
            access_level=self.access_level,
        )
