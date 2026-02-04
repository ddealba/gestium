"""Employee model."""

from __future__ import annotations

import uuid

from app.extensions import db
from app.models.base import BaseModel


class Employee(BaseModel):
    """Represents an employee belonging to a company."""

    __tablename__ = "employees"
    __table_args__ = (
        db.CheckConstraint(
            "(status = 'terminated' AND end_date IS NOT NULL AND end_date >= start_date) "
            "OR (status = 'active' AND end_date IS NULL)",
            name="ck_employees_status_dates",
        ),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey("clients.id"), nullable=False, index=True)
    company_id = db.Column(db.String(36), db.ForeignKey("companies.id"), nullable=False, index=True)
    full_name = db.Column(db.String(255), nullable=False)
    employee_ref = db.Column(db.String(255), nullable=True)
    status = db.Column(
        db.Enum("active", "terminated", name="employee_status"),
        nullable=False,
        default="active",
    )
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)

    company = db.relationship("Company", backref=db.backref("employees", lazy="dynamic"))

    def __repr__(self) -> str:
        return (
            "<Employee id={id} client_id={client_id} company_id={company_id} "
            "full_name={full_name} status={status}>"
        ).format(
            id=self.id,
            client_id=self.client_id,
            company_id=self.company_id,
            full_name=self.full_name,
            status=self.status,
        )
