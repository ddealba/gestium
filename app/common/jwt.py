"""JWT helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from flask import current_app
from werkzeug.exceptions import Unauthorized


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _sign(message: bytes, secret: str) -> str:
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()
    return _base64url_encode(signature)


def create_access_token(user_id: str, client_id: str, expires_minutes: int = 60) -> str:
    """Create a signed access token."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "client_id": str(client_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expires_minutes)).timestamp()),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = _sign(signing_input, current_app.config["SECRET_KEY"])
    return f"{encoded_header}.{encoded_payload}.{signature}"


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        encoded_header, encoded_payload, signature = token.split(".")
    except ValueError as exc:
        raise Unauthorized("invalid_token") from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    expected_signature = _sign(signing_input, current_app.config["SECRET_KEY"])
    if not hmac.compare_digest(signature, expected_signature):
        raise Unauthorized("invalid_token")

    try:
        payload = json.loads(_base64url_decode(encoded_payload))
    except (ValueError, json.JSONDecodeError) as exc:
        raise Unauthorized("invalid_token") from exc

    exp = payload.get("exp")
    if exp is None:
        raise Unauthorized("invalid_token")
    now = datetime.now(timezone.utc).timestamp()
    if now > float(exp):
        raise Unauthorized("token_expired")

    return payload
