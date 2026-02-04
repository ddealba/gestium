"""Helpers for company-level ACL enforcement."""

from __future__ import annotations

from typing import Any

from flask import g, has_request_context, request
from werkzeug.exceptions import BadRequest

from app.services.company_access_service import CompanyAccessService

_CACHE_ATTR = "_company_access_cache"


def resolve_company_id(company_id_arg: str | None = None) -> str:
    """Resolve a company_id from request path params or a provided argument."""
    company_id = None
    if request.view_args:
        if company_id_arg and company_id_arg in request.view_args:
            company_id = request.view_args.get(company_id_arg)
        elif "company_id" in request.view_args:
            company_id = request.view_args.get("company_id")

    if company_id is None and company_id_arg:
        company_id = request.args.get(company_id_arg)
        if company_id is None:
            payload = request.get_json(silent=True) or {}
            company_id = payload.get(company_id_arg)

    if not company_id:
        raise BadRequest("company_id_required")

    return str(company_id)


def get_allowed_company_ids(user_id: str, client_id: str) -> set[str]:
    """Return allowed company ids for the user, cached per request."""
    cache = _get_request_cache()
    cache_key = ("allowed_company_ids", user_id, client_id)
    if cache_key in cache:
        return cache[cache_key]

    allowed = CompanyAccessService().get_allowed_company_ids(user_id, client_id)
    cache[cache_key] = allowed
    return allowed


def _get_request_cache() -> dict[tuple[Any, ...], Any]:
    if has_request_context():
        cache = getattr(g, _CACHE_ATTR, None)
        if cache is None:
            cache = {}
            setattr(g, _CACHE_ATTR, cache)
        return cache
    return {}
