"""Service layer for platform-level tenant management."""

from __future__ import annotations

from werkzeug.exceptions import NotFound

from app.models.client import Client
from app.models.user import User
from app.modules.platform_admin.repository import ClientRepositoryPlatform
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository


class PlatformAdminService:
    """Business logic for cross-tenant administration."""

    def __init__(
        self,
        repository: ClientRepositoryPlatform | None = None,
        user_repository: UserRepository | None = None,
        role_repository: RoleRepository | None = None,
    ) -> None:
        self.repository = repository or ClientRepositoryPlatform()
        self.user_repository = user_repository or UserRepository()
        self.role_repository = role_repository or RoleRepository()

    def list_tenants(
        self,
        q: str | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        tenants, total = self.repository.list_clients(q=q, status=status, limit=limit, offset=offset)
        tenant_ids = [tenant.id for tenant in tenants]
        company_counts = self.repository.count_companies_by_client_ids(tenant_ids)
        user_counts = self.repository.count_users_by_client_ids(tenant_ids)

        items = [
            {
                "id": tenant.id,
                "name": tenant.name,
                "status": tenant.status,
                "plan": tenant.plan,
                "logo_url": getattr(tenant, "logo_url", None),
                "metrics": {
                    "companies": int(company_counts.get(tenant.id, 0)),
                    "users": int(user_counts.get(tenant.id, 0)),
                },
                "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
            }
            for tenant in tenants
        ]
        return items, total


    def get_tenant_detail(self, tenant_id: str) -> dict:
        tenant = self.repository.get_client(tenant_id)
        if tenant is None:
            raise NotFound("tenant_not_found")

        company_count = self.repository.count_companies_by_client_ids([tenant.id]).get(tenant.id, 0)
        user_count = self.repository.count_users_by_client_ids([tenant.id]).get(tenant.id, 0)

        companies = self.repository.list_companies_for_client(tenant.id)
        users = self.repository.list_users_for_client(tenant.id)

        return {
            "id": tenant.id,
            "name": tenant.name,
            "status": tenant.status,
            "plan": tenant.plan,
            "logo_url": getattr(tenant, "logo_url", None),
            "created_at": tenant.created_at.isoformat() if tenant.created_at else None,
            "metrics": {
                "companies": int(company_count),
                "users": int(user_count),
            },
            "companies": [
                {
                    "id": company.id,
                    "name": company.name,
                    "tax_id": company.tax_id,
                    "status": company.status,
                }
                for company in companies
            ],
            "users": [
                {
                    "id": user.id,
                    "email": user.email,
                    "status": user.status,
                }
                for user in users
            ],
        }

    def create_tenant(self, payload: dict) -> Client:
        client_values = {
            "name": payload["name"],
            "plan": payload.get("plan"),
            "status": payload.get("status") or "active",
        }
        if hasattr(Client, "logo_url"):
            client_values["logo_url"] = payload.get("logo_url")

        tenant = self.repository.create_client(**client_values)

        admin_email = payload.get("admin_email")
        if admin_email:
            self._create_initial_tenant_admin(tenant_id=tenant.id, email=admin_email)

        return tenant

    def update_tenant(self, tenant_id: str, payload: dict) -> Client:
        tenant = self.repository.get_client(tenant_id)
        if tenant is None:
            raise NotFound("tenant_not_found")

        for field in ("name", "status", "plan"):
            if field in payload and payload[field] is not None:
                setattr(tenant, field, payload[field])

        if hasattr(tenant, "logo_url") and "logo_url" in payload:
            tenant.logo_url = payload.get("logo_url")

        return self.repository.update_client(tenant)

    def _create_initial_tenant_admin(self, tenant_id: str, email: str) -> User:
        user = self.user_repository.get_by_email(email, tenant_id)
        if user is None:
            user = User(client_id=tenant_id, email=email, status="invited")
            self.user_repository.create(user)

        admin_role = self.role_repository.get_by_name(
            name="Admin Cliente",
            scope="tenant",
            client_id=tenant_id,
        )
        if admin_role and admin_role not in user.roles:
            user.roles.append(admin_role)
            self.user_repository.update(user)
        return user
