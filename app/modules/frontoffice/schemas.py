"""Schemas/helpers for frontoffice payload formatting."""

from __future__ import annotations


def serialize_profile(person) -> dict:
    return {
        "person_id": person.id,
        "first_name": person.first_name,
        "last_name": person.last_name,
        "document_number": person.document_number,
        "email": person.email,
        "phone": person.phone,
        "address": person.address_line1,
        "address_line1": person.address_line1,
        "city": person.city,
        "postal_code": person.postal_code,
        "country": person.country,
        "status": person.status,
    }


def serialize_document(document, scope: str | None = None) -> dict:
    resolved_scope = scope
    if resolved_scope is None:
        if document.person_id:
            resolved_scope = "person"
        elif document.employee_id:
            resolved_scope = "employee"
        elif document.company_id:
            resolved_scope = "company"
        else:
            resolved_scope = "unknown"

    return {
        "id": document.id,
        "file_name": document.original_filename,
        "doc_type": document.doc_type,
        "status": document.status,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "company_id": document.company_id,
        "company_name": document.company.name if document.company else None,
        "person_id": document.person_id,
        "employee_id": document.employee_id,
        "scope": resolved_scope,
    }


def serialize_case(case_item, scope: str | None = None) -> dict:
    resolved_scope = scope
    if resolved_scope is None:
        resolved_scope = "person" if case_item.person_id else "company"

    return {
        "id": case_item.id,
        "title": case_item.title,
        "type": case_item.type,
        "status": case_item.status,
        "due_date": case_item.due_date.isoformat() if case_item.due_date else None,
        "company_id": case_item.company_id,
        "company_name": case_item.company.name if case_item.company else None,
        "person_id": case_item.person_id,
        "scope": resolved_scope,
    }


def serialize_company_relation(relation) -> dict:
    return {
        "company_id": relation.company_id,
        "company_name": relation.company.name if relation.company else None,
        "relation_type": relation.relation_type,
        "status": relation.status,
    }
