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
        "status": person.status,
    }


def serialize_document(document) -> dict:
    return {
        "id": document.id,
        "file_name": document.original_filename,
        "doc_type": document.doc_type,
        "status": document.status,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "company_name": document.company.name if document.company else None,
    }


def serialize_case(case_item) -> dict:
    return {
        "id": case_item.id,
        "title": case_item.title,
        "type": case_item.type,
        "status": case_item.status,
        "due_date": case_item.due_date.isoformat() if case_item.due_date else None,
        "company_name": case_item.company.name if case_item.company else None,
    }


def serialize_company_relation(relation) -> dict:
    return {
        "company_id": relation.company_id,
        "company_name": relation.company.name if relation.company else None,
        "relation_type": relation.relation_type,
    }
