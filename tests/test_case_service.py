import pytest
from werkzeug.exceptions import BadRequest

from app.extensions import db
from app.models.case import Case
from app.models.case_event import CaseEvent
from app.models.client import Client
from app.models.company import Company
from app.models.user import User
from app.modules.cases.service import CaseService


def _create_client() -> Client:
    client = Client(name="Acme")
    db.session.add(client)
    db.session.commit()
    return client


def _create_company(client_id: str) -> Company:
    company = Company(client_id=client_id, name="Alpha", tax_id="A-123")
    db.session.add(company)
    db.session.commit()
    return company


def _create_user(client_id: str, email: str) -> User:
    user = User(client_id=client_id, email=email, status="active")
    db.session.add(user)
    db.session.commit()
    return user


def test_create_case_creates_default_open_status_and_initial_event(app):
    with app.app_context():
        db.create_all()
        tenant = _create_client()
        company = _create_company(tenant.id)
        actor = _create_user(tenant.id, "owner@example.com")

        service = CaseService()
        case = service.create_case(
            client_id=tenant.id,
            company_id=company.id,
            actor_user_id=actor.id,
            payload={"title": "Nuevo expediente", "description": "Texto inicial"},
        )
        db.session.commit()

        assert case.status == "open"
        events = (
            db.session.query(CaseEvent)
            .filter(CaseEvent.case_id == case.id)
            .order_by(CaseEvent.created_at.asc())
            .all()
        )
        assert len(events) == 1
        assert events[0].event_type == "status_change"
        assert events[0].payload == {"from": None, "to": "open"}

        db.drop_all()


def test_change_status_blocks_reopening_terminal_cases(app):
    with app.app_context():
        db.create_all()
        tenant = _create_client()
        company = _create_company(tenant.id)
        actor = _create_user(tenant.id, "owner@example.com")

        service = CaseService()
        case = service.create_case(
            client_id=tenant.id,
            company_id=company.id,
            actor_user_id=actor.id,
            payload={"title": "Caso 1"},
        )
        service.change_status(tenant.id, company.id, case.id, actor.id, "done")
        db.session.commit()

        with pytest.raises(BadRequest) as exc_info:
            service.change_status(tenant.id, company.id, case.id, actor.id, "open")
        assert exc_info.value.description == "invalid_status_transition"

        db.drop_all()


def test_assign_and_comment_generate_events(app):
    with app.app_context():
        db.create_all()
        tenant = _create_client()
        company = _create_company(tenant.id)
        actor = _create_user(tenant.id, "owner@example.com")
        responsible = _create_user(tenant.id, "assigned@example.com")

        service = CaseService()
        case = service.create_case(
            client_id=tenant.id,
            company_id=company.id,
            actor_user_id=actor.id,
            payload={"title": "Caso 2", "comment": "Comentario inicial"},
        )
        service.assign_responsible(tenant.id, company.id, case.id, actor.id, responsible.id)
        service.add_comment(tenant.id, company.id, case.id, actor.id, "Seguimiento")
        db.session.commit()

        assigned_case = db.session.query(Case).filter(Case.id == case.id).one()
        assert assigned_case.responsible_user_id == responsible.id

        event_types = [
            event.event_type
            for event in db.session.query(CaseEvent)
            .filter(CaseEvent.case_id == case.id)
            .order_by(CaseEvent.created_at.asc())
            .all()
        ]
        assert event_types == ["comment", "assignment", "comment"]

        db.drop_all()
