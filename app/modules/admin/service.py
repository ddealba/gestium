"""Tenant admin user management service."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import or_
from werkzeug.exceptions import BadRequest, NotFound

from app.models.role import Role
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.services.invitation_service import InvitationResult, InvitationService


@dataclass(frozen=True)
class PaginatedUsers:
    items: list[User]
    total: int
    page: int
    per_page: int


class TenantAdminService:
    """Business logic for tenant admin operations on users and roles."""

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        role_repository: RoleRepository | None = None,
        invitation_service: InvitationService | None = None,
    ) -> None:
        self.user_repository = user_repository or UserRepository()
        self.role_repository = role_repository or RoleRepository()
        self.invitation_service = invitation_service or InvitationService(
            user_repository=self.user_repository,
        )

    def list_users(self, client_id: str, page: int | None, per_page: int | None) -> PaginatedUsers:
        query = self.user_repository.session.query(User).filter(User.client_id == client_id)
        total = query.count()
        ordered = query.order_by(User.created_at.desc())

        if page is None or per_page is None:
            items = ordered.all()
            return PaginatedUsers(items=items, total=total, page=1, per_page=total or 1)

        if page < 1 or per_page < 1:
            raise BadRequest("invalid_pagination")

        items = ordered.offset((page - 1) * per_page).limit(per_page).all()
        return PaginatedUsers(items=items, total=total, page=page, per_page=per_page)

    def invite_user(self, client_id: str, email: str, role_ids: list[str] | None, role_names: list[str] | None) -> InvitationResult:
        if role_ids and role_names:
            raise BadRequest("roles_payload_conflict")

        invitation_result = self.invitation_service.create_invitation(client_id, email)

        if role_ids or role_names:
            roles = self._resolve_roles(client_id, role_ids=role_ids, role_names=role_names)
            user = self.user_repository.get_by_email(invitation_result.invitation.email, client_id)
            if user is None:
                raise BadRequest("invited_user_missing")
            user.roles = roles
            self.user_repository.update(user)

        return invitation_result

    def disable_user(self, client_id: str, user_id: str) -> User:
        user = self._get_tenant_user(client_id, user_id)
        user.status = "disabled"
        return self.user_repository.update(user)

    def enable_user(self, client_id: str, user_id: str) -> User:
        user = self._get_tenant_user(client_id, user_id)
        if user.status == "invited" and not user.password_hash:
            raise BadRequest("user_not_activated")
        user.status = "active"
        return self.user_repository.update(user)

    def replace_roles(
        self,
        client_id: str,
        user_id: str,
        role_ids: list[str] | None,
        role_names: list[str] | None,
    ) -> list[Role]:
        if role_ids is None and role_names is None:
            raise BadRequest("roles_required")
        if role_ids is not None and role_names is not None:
            raise BadRequest("roles_payload_conflict")

        user = self._get_tenant_user(client_id, user_id)
        roles = self._resolve_roles(client_id, role_ids=role_ids, role_names=role_names)
        user.roles = roles
        self.user_repository.update(user)
        return list(user.roles)

    def list_roles(self, client_id: str) -> list[Role]:
        return (
            self.role_repository.session.query(Role)
            .filter(
                or_(
                    (Role.scope == "tenant") & (Role.client_id == client_id),
                    (Role.scope == "platform") & (Role.client_id.is_(None)),
                )
            )
            .order_by(Role.scope.asc(), Role.name.asc())
            .all()
        )

    def _get_tenant_user(self, client_id: str, user_id: str) -> User:
        user = self.user_repository.get_by_id(user_id, client_id)
        if user is None:
            raise NotFound("user_not_found")
        return user

    def _resolve_roles(self, client_id: str, role_ids: list[str] | None, role_names: list[str] | None) -> list[Role]:
        if role_ids is not None:
            resolved_roles = []
            for role_id in role_ids:
                role = self.role_repository.get_by_id(role_id)
                if role is None or (role.scope == "tenant" and role.client_id != client_id):
                    raise NotFound("role_not_found")
                resolved_roles.append(role)
            return resolved_roles

        if role_names is not None:
            resolved_roles = []
            for role_name in role_names:
                role = (
                    self.role_repository.session.query(Role)
                    .filter(
                        Role.name == role_name,
                        or_(
                            (Role.scope == "tenant") & (Role.client_id == client_id),
                            (Role.scope == "platform") & (Role.client_id.is_(None)),
                        ),
                    )
                    .one_or_none()
                )
                if role is None:
                    raise NotFound("role_not_found")
                resolved_roles.append(role)
            return resolved_roles

        return []
