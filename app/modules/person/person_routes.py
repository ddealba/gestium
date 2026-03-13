"""Person API routes."""

from __future__ import annotations

from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest, Conflict
from werkzeug.security import generate_password_hash

from app.common.decorators import auth_required, require_permission
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.extensions import db
from app.modules.person.person_completeness_service import PersonCompletenessService
from app.modules.person.person_schemas import PersonCreateRequest, PersonResponseSchema, PersonUpdateRequest
from app.modules.person.person_overview_service import PersonOverviewService
from app.modules.person.person_service import PersonService
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService
from app.services.invitation_service import InvitationService
from app.models.user import User
from app.modules.notification.notification_service import NotificationService

bp = Blueprint("person", __name__)


def _parse_int_arg(name: str, default: int) -> int:
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise BadRequest(f"invalid_{name}") from exc


@bp.get("/persons")
@auth_required
@tenant_required
@require_permission("person.read")
def list_persons():
    service = PersonService()
    page = _parse_int_arg("page", 1)
    limit = _parse_int_arg("limit", 20)
    search = (request.args.get("search") or "").strip()
    status = request.args.get("status")

    if search:
        items, total = service.search_persons(str(g.client_id), search=search, status=status, page=page, limit=limit)
    else:
        items, total = service.list_persons(str(g.client_id), status=status, page=page, limit=limit)

    return ok({
        "items": [PersonResponseSchema.dump(person) for person in items],
        "total": total,
        "page": max(page, 1),
        "limit": max(limit, 1),
    })


@bp.get("/persons/<person_id>")
@auth_required
@tenant_required
@require_permission("person.read")
def get_person(person_id: str):
    service = PersonService()
    person = service.get_person(str(g.client_id), person_id)
    return ok({"person": PersonResponseSchema.dump(person)})


@bp.get("/persons/<person_id>/overview")
@auth_required
@tenant_required
@require_permission("person.read")
def get_person_overview(person_id: str):
    overview = PersonOverviewService().build_overview(str(g.client_id), person_id)
    return ok(overview)




@bp.get("/persons/<person_id>/completeness")
@auth_required
@tenant_required
@require_permission("person.read")
def get_person_completeness(person_id: str):
    PersonService().get_person(str(g.client_id), person_id)
    completeness = PersonCompletenessService().get_person_completeness(person_id, str(g.client_id))
    return ok({"completeness": completeness})


@bp.post("/persons/<person_id>/generate-requests")
@auth_required
@tenant_required
@require_permission("person.write")
def generate_person_requests(person_id: str):
    PersonService().get_person(str(g.client_id), person_id)
    payload = request.get_json(silent=True) or {}
    force_regenerate = bool(payload.get("force_regenerate", False))
    service = PersonCompletenessService()
    created = service.generate_pending_requests(
        client_id=str(g.client_id),
        person_id=person_id,
        actor_user_id=str(g.user.id),
        force_regenerate=force_regenerate,
    )
    db.session.commit()
    return ok({"created": len(created), "requests": [{"id": item.id, "title": item.title, "type": item.request_type} for item in created]})


@bp.post("/persons")
@auth_required
@tenant_required
@require_permission("person.write")
def create_person():
    payload = request.get_json(silent=True) or {}
    create_payload = PersonCreateRequest.from_dict(payload)
    service = PersonService()
    person = service.create_person(str(g.client_id), str(g.user.id), create_payload)
    PersonCompletenessService().generate_pending_requests(
        client_id=str(g.client_id),
        person_id=person.id,
        actor_user_id=str(g.user.id),
    )
    db.session.commit()
    return ok({"person": PersonResponseSchema.dump(person)}, status_code=201)


@bp.put("/persons/<person_id>")
@auth_required
@tenant_required
@require_permission("person.write")
def update_person(person_id: str):
    payload = request.get_json(silent=True) or {}
    update_payload = PersonUpdateRequest.from_dict(payload)
    service = PersonService()
    person = service.update_person(str(g.client_id), str(g.user.id), person_id, update_payload)
    db.session.commit()
    return ok({"person": PersonResponseSchema.dump(person)})


@bp.get("/persons/<person_id>/portal-user")
@auth_required
@tenant_required
@require_permission("tenant.user.read")
def get_person_portal_user(person_id: str):
    person = PersonService().get_person(str(g.client_id), person_id)
    user = (
        UserRepository()
        .session.query(User)
        .filter(
            User.client_id == str(g.client_id),
            User.person_id == person.id,
            User.user_type == "portal",
        )
        .order_by(User.created_at.desc())
        .first()
    )
    if user is None:
        return ok({"portal_user": None})
    return ok(
        {
            "portal_user": {
                "id": user.id,
                "email": user.email,
                "status": user.status,
                "person_id": user.person_id,
                "user_type": user.user_type,
            }
        }
    )


@bp.post("/persons/<person_id>/portal-user")
@auth_required
@tenant_required
@require_permission("tenant.user.manage")
def upsert_person_portal_user(person_id: str):
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip()
    password = payload.get("password")
    if not email:
        raise BadRequest("email_required")
    if not password or len(password) < 8:
        raise BadRequest("password_too_short")

    person = PersonService().get_person(str(g.client_id), person_id)
    user_repo = UserRepository()
    user_service = UserService(user_repo)
    normalized_email = user_service.normalize_email(email)

    existing_by_email = user_repo.get_by_email(normalized_email, str(g.client_id))
    if existing_by_email and existing_by_email.person_id and existing_by_email.person_id != person.id:
        raise Conflict("email_already_in_use")

    portal_user = (
        user_repo.session.query(User)
        .filter(
            User.client_id == str(g.client_id),
            User.person_id == person.id,
            User.user_type == "portal",
        )
        .order_by(User.created_at.desc())
        .first()
    )

    target = portal_user or existing_by_email
    created_now = False
    if target is None:
        created_now = True
        target = User(
            client_id=str(g.client_id),
            email=normalized_email,
            status="active",
            user_type="portal",
            person_id=person.id,
            password_hash=generate_password_hash(password),
        )
        user_repo.create(target)
    else:
        target.email = normalized_email
        target.user_type = "portal"
        target.person_id = person.id
        target.status = "active"
        target.password_hash = generate_password_hash(password)
        user_repo.update(target)

    completeness_service = PersonCompletenessService()
    completeness_service.recalculate_person_status(person, actor_user_id=str(g.user.id))
    if created_now:
        NotificationService().create_portal_notification(
            client_id=str(g.client_id),
            person_id=person.id,
            user_id=target.id,
            notification_type="portal_access_created",
            title="Acceso al portal activado",
            message="Tu acceso al portal está listo.",
            entity_type="person",
            entity_id=person.id,
            priority="medium",
            deduplicate=True,
        )
    db.session.commit()
    return ok(
        {
            "portal_user": {
                "id": target.id,
                "email": target.email,
                "status": target.status,
                "person_id": target.person_id,
                "user_type": target.user_type,
            }
        }
    )


@bp.post("/persons/<person_id>/portal-user/invite")
@auth_required
@tenant_required
@require_permission("tenant.user.manage")
def invite_person_portal_user(person_id: str):
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip()
    if not email:
        raise BadRequest("email_required")

    person = PersonService().get_person(str(g.client_id), person_id)
    user_repo = UserRepository()
    user_service = UserService(user_repo)
    normalized_email = user_service.normalize_email(email)

    existing_by_email = user_repo.get_by_email(normalized_email, str(g.client_id))
    if existing_by_email and existing_by_email.person_id and existing_by_email.person_id != person.id:
        raise Conflict("email_already_in_use")

    portal_user = (
        user_repo.session.query(User)
        .filter(
            User.client_id == str(g.client_id),
            User.person_id == person.id,
            User.user_type == "portal",
        )
        .order_by(User.created_at.desc())
        .first()
    )

    target = portal_user or existing_by_email
    if target is None:
        target = User(
            client_id=str(g.client_id),
            email=normalized_email,
            status="invited",
            user_type="portal",
            person_id=person.id,
            password_hash=None,
        )
        user_repo.create(target)
    else:
        target.email = normalized_email
        target.user_type = "portal"
        target.person_id = person.id
        if target.status == "disabled":
            target.status = "invited"
        user_repo.update(target)

    invitation = InvitationService(user_repository=user_repo).create_invitation(str(g.client_id), normalized_email)
    PersonCompletenessService().recalculate_person_status(person, actor_user_id=str(g.user.id))
    db.session.commit()

    activation_link = f"/portal/activate?token={invitation.token}"
    return ok(
        {
            "portal_user": {
                "id": target.id,
                "email": target.email,
                "status": target.status,
                "person_id": target.person_id,
                "user_type": target.user_type,
            },
            "invite_token": invitation.token,
            "activation_link": activation_link,
            "expires_at": invitation.invitation.expires_at.isoformat(),
        }
    )


@bp.post("/persons/<person_id>/portal-user/disable")
@auth_required
@tenant_required
@require_permission("tenant.user.manage")
def disable_person_portal_user(person_id: str):
    person = PersonService().get_person(str(g.client_id), person_id)
    user = (
        UserRepository()
        .session.query(User)
        .filter(
            User.client_id == str(g.client_id),
            User.person_id == person.id,
            User.user_type == "portal",
        )
        .order_by(User.created_at.desc())
        .first()
    )
    if user is None:
        raise BadRequest("portal_user_not_found")
    user.status = "disabled"
    db.session.add(user)
    PersonCompletenessService().recalculate_person_status(person, actor_user_id=str(g.user.id))
    db.session.commit()
    return ok(
        {
            "portal_user": {
                "id": user.id,
                "email": user.email,
                "status": user.status,
                "person_id": user.person_id,
                "user_type": user.user_type,
            }
        }
    )
