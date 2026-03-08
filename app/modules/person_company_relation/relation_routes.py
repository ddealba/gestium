"""API routes for person-company relations."""

from __future__ import annotations

from flask import Blueprint, g, request

from app.common.decorators import auth_required, require_permission
from app.common.responses import ok
from app.common.tenant import tenant_required
from app.extensions import db
from app.modules.person_company_relation.relation_schemas import (
    PersonCompanyRelationCreateRequest,
    PersonCompanyRelationResponseSchema,
    PersonCompanyRelationUpdateRequest,
)
from app.modules.person_company_relation.relation_service import PersonCompanyRelationService

bp = Blueprint("person_company_relations", __name__)


@bp.get("/persons/<person_id>/companies")
@auth_required
@tenant_required
@require_permission("person.read")
def list_person_companies(person_id: str):
    service = PersonCompanyRelationService()
    return ok({"items": service.get_person_relations(str(g.client_id), person_id)})


@bp.post("/persons/<person_id>/companies")
@auth_required
@tenant_required
@require_permission("person.write")
@require_permission("company.write")
def create_person_company_relation(person_id: str):
    payload = request.get_json(silent=True) or {}
    create_payload = PersonCompanyRelationCreateRequest.from_dict(payload)
    service = PersonCompanyRelationService()
    relation = service.create_person_company_relation(
        client_id=str(g.client_id),
        user_id=str(g.user.id),
        person_id=person_id,
        payload=create_payload,
    )
    db.session.commit()
    return ok({"relation": PersonCompanyRelationResponseSchema.dump(relation)}, status_code=201)


@bp.get("/companies/<company_id>/persons")
@auth_required
@tenant_required
@require_permission("company.read")
def list_company_persons(company_id: str):
    service = PersonCompanyRelationService()
    return ok({"items": service.get_company_relations(str(g.client_id), company_id)})


@bp.patch("/person-company-relations/<relation_id>")
@auth_required
@tenant_required
@require_permission("person.write")
@require_permission("company.write")
def update_person_company_relation(relation_id: str):
    payload = request.get_json(silent=True) or {}
    update_payload = PersonCompanyRelationUpdateRequest.from_dict(payload)
    service = PersonCompanyRelationService()
    relation = service.update_person_company_relation(
        client_id=str(g.client_id),
        user_id=str(g.user.id),
        relation_id=relation_id,
        payload=update_payload,
    )
    db.session.commit()
    return ok({"relation": PersonCompanyRelationResponseSchema.dump(relation)})


@bp.post("/person-company-relations/<relation_id>/deactivate")
@auth_required
@tenant_required
@require_permission("person.write")
@require_permission("company.write")
def deactivate_person_company_relation(relation_id: str):
    service = PersonCompanyRelationService()
    relation = service.deactivate_person_company_relation(
        client_id=str(g.client_id),
        user_id=str(g.user.id),
        relation_id=relation_id,
    )
    db.session.commit()
    return ok({"relation": PersonCompanyRelationResponseSchema.dump(relation)})
