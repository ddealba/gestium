"""Auth routes."""

from flask import Blueprint, g, request
from werkzeug.exceptions import BadRequest

from app.common.decorators import auth_required, noop_decorator
from app.common.jwt import create_access_token
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.extensions import db, limiter
from app.services.auth_service import AuthService
from app.services.invitation_service import InvitationService

bp = Blueprint("auth", __name__)

require_permission = noop_decorator


@bp.post("/auth/invite")
@tenant_required
@require_permission
def invite_user():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    if not email:
        raise BadRequest("email_required")

    service = InvitationService()
    result = service.create_invitation(str(g.client_id), email)
    db.session.commit()

    return ok(
        {
            "invite_token": result.token,
            "expires_at": result.invitation.expires_at.isoformat(),
        },
        status_code=201,
    )


@bp.post("/auth/activate")
@tenant_required
@require_permission
def activate_user():
    payload = request.get_json(silent=True) or {}
    token = payload.get("token")
    password = payload.get("password")
    if not token:
        raise BadRequest("token_required")
    if not password:
        raise BadRequest("password_required")

    service = InvitationService()
    service.consume_invitation(str(g.client_id), token, password)
    db.session.commit()

    return ok({"status": "active"})


@bp.post("/auth/login")
@limiter.limit("10/minute")
def login_user():
    payload = request.get_json(silent=True) or {}
    email = payload.get("email")
    password = payload.get("password")
    client_id = payload.get("client_id")

    service = AuthService()
    user_id, resolved_client_id = service.authenticate(email, password, client_id)
    token = create_access_token(user_id, resolved_client_id)

    return ok(
        {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 3600,
        }
    )


@bp.get("/auth/me")
@auth_required
def get_current_user():
    user = g.user
    return ok(
        {
            "id": user.id,
            "email": user.email,
            "client_id": user.client_id,
            "status": user.status,
        }
    )
