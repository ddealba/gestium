"""Access level definitions and helpers for company ACLs."""

from __future__ import annotations

from enum import Enum


class AccessLevel(str, Enum):
    """Ordered access levels for company ACLs."""

    viewer = "viewer"
    operator = "operator"
    manager = "manager"
    admin = "admin"


ACCESS_LEVEL_ORDER: dict[AccessLevel, int] = {
    AccessLevel.viewer: 0,
    AccessLevel.operator: 1,
    AccessLevel.manager: 2,
    AccessLevel.admin: 3,
}


def _normalize_level(level: str | AccessLevel) -> AccessLevel:
    if isinstance(level, AccessLevel):
        return level
    try:
        return AccessLevel(level)
    except ValueError as exc:
        raise ValueError(f"Unknown access level: {level}") from exc


def access_level_ge(user_level: str | AccessLevel, required_level: str | AccessLevel) -> bool:
    """Return True if the user level meets or exceeds the required level."""
    normalized_user = _normalize_level(user_level)
    normalized_required = _normalize_level(required_level)
    return ACCESS_LEVEL_ORDER[normalized_user] >= ACCESS_LEVEL_ORDER[normalized_required]
