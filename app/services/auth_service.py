"""Authentication service."""

from __future__ import annotations

from app.modules.auth.service import AuthService as ModuleAuthService


class AuthService(ModuleAuthService):
    """# DEPRECATED: use app.modules.auth.service.AuthService."""
