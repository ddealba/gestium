"""Backward-compatible serializers for legacy frontoffice imports."""

from app.modules.portal.schemas import (
    serialize_case,
    serialize_company_relation,
    serialize_document,
    serialize_profile,
)

__all__ = [
    "serialize_profile",
    "serialize_document",
    "serialize_case",
    "serialize_company_relation",
]
