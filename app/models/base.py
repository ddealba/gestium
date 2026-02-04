"""Base model definitions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.extensions import db


class BaseModel(db.Model):
    """Common base model with timestamps and serialization helpers."""

    __abstract__ = True

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def as_dict(self) -> dict[str, Any]:
        """Return a dict representation of the model."""
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}
