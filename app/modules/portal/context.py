"""Portal request context helpers."""

from __future__ import annotations

from dataclasses import dataclass

from werkzeug.exceptions import Forbidden


@dataclass(frozen=True)
class PortalContext:
    """Resolved context for authenticated portal users."""

    user_id: str
    person_id: str
    client_id: str

    @classmethod
    def from_user(cls, current_user, client_id: str) -> "PortalContext":
        if current_user is None:
            raise Forbidden("portal_user_required")
        if (getattr(current_user, "user_type", "") or "").lower() != "portal":
            raise Forbidden("invalid_user_type")
        person_id = getattr(current_user, "person_id", None)
        if not person_id:
            raise Forbidden("portal_user_requires_person")
        return cls(user_id=str(current_user.id), person_id=str(person_id), client_id=str(client_id))
