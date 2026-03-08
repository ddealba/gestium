"""Repository for person requests."""

from __future__ import annotations

from sqlalchemy import func

from app.extensions import db
from app.models.person_request import PersonRequest


class PersonRequestRepository:
    def add(self, item: PersonRequest) -> PersonRequest:
        db.session.add(item)
        return item

    @staticmethod
    def get_by_id(client_id: str, request_id: str) -> PersonRequest | None:
        return (
            db.session.query(PersonRequest)
            .filter(PersonRequest.client_id == client_id, PersonRequest.id == request_id)
            .one_or_none()
        )

    @staticmethod
    def list_person_requests(
        client_id: str,
        person_id: str,
        status: str | None = None,
        request_type: str | None = None,
    ) -> list[PersonRequest]:
        query = db.session.query(PersonRequest).filter(
            PersonRequest.client_id == client_id,
            PersonRequest.person_id == person_id,
        )
        if status:
            query = query.filter(PersonRequest.status == status)
        if request_type:
            query = query.filter(PersonRequest.request_type == request_type)
        return query.order_by(
            func.coalesce(PersonRequest.due_date, func.current_date()).asc(),
            PersonRequest.created_at.desc(),
        ).all()
