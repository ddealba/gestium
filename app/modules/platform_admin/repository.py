"""Repository for platform-level tenant management."""

from __future__ import annotations

from sqlalchemy import func, or_

from app.extensions import db
from app.models.client import Client
from app.models.company import Company
from app.models.user import User


class ClientRepositoryPlatform:
    """Data access for clients without tenant scoping."""

    def __init__(self, session: db.Session | None = None) -> None:
        self.session = session or db.session

    def list_clients(
        self,
        q: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Client], int]:
        query = self.session.query(Client)

        if status:
            query = query.filter(Client.status == status)

        if q is not None:
            q_value = q.strip()
            if q_value:
                like_query = f"%{q_value}%"
                query = query.filter(
                    or_(
                        Client.name.ilike(like_query),
                        Client.plan.ilike(like_query),
                    )
                )

        total = query.count()
        items = (
            query.order_by(Client.created_at.desc())
            .limit(max(limit, 1))
            .offset(max(offset, 0))
            .all()
        )
        return items, total

    def create_client(self, **kwargs) -> Client:
        client = Client(**kwargs)
        self.session.add(client)
        self.session.flush()
        return client

    def update_client(self, client: Client) -> Client:
        self.session.add(client)
        self.session.flush()
        return client

    def get_client(self, client_id: str) -> Client | None:
        return self.session.query(Client).filter(Client.id == client_id).one_or_none()

    def count_companies_by_client_ids(self, client_ids: list[str]) -> dict[str, int]:
        if not client_ids:
            return {}

        rows = (
            self.session.query(Company.client_id, func.count(Company.id))
            .filter(Company.client_id.in_(client_ids))
            .group_by(Company.client_id)
            .all()
        )
        return {client_id: count for client_id, count in rows}

    def count_users_by_client_ids(self, client_ids: list[str]) -> dict[str, int]:
        if not client_ids:
            return {}

        rows = (
            self.session.query(User.client_id, func.count(User.id))
            .filter(User.client_id.in_(client_ids))
            .group_by(User.client_id)
            .all()
        )
        return {client_id: count for client_id, count in rows}
