"""merge person requests and portal fields heads

Revision ID: d5e6f7a8b9c0
Revises: b2c3d4e5f6a7, c9d8e7f6a5b4
Create Date: 2026-03-08 20:50:00.000000
"""

from __future__ import annotations

revision = "d5e6f7a8b9c0"
down_revision = ("b2c3d4e5f6a7", "c9d8e7f6a5b4")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge heads without schema changes."""


def downgrade() -> None:
    """Unmerge heads without schema changes."""
