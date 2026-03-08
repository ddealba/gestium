from datetime import date
import uuid

from app.common.jwt import create_access_token
from app.extensions import db
from app.models.case import Case
from app.models.client import Client
from app.models.company import Company
from app.models.document import Document
from app.models.employee import Employee
from app.models.person import Person
from app.models.person_company_relation import PersonCompanyRelation
from app.models.user import User


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_portal_access_and_advanced_visibility(client, app):
    with app.app_context():
        db.create_all()

        tenant = Client(name=f"Tenant A {uuid.uuid4()}", status="active")
        db.session.add(tenant)
        db.session.flush()

        company_owner = Company(client_id=tenant.id, name="Empresa Owner", tax_id="EO1", status="active")
        company_foreign = Company(client_id=tenant.id, name="Empresa Ajena", tax_id="EA1", status="active")
        db.session.add_all([company_owner, company_foreign])
        db.session.flush()

        person_portal = Person(
            client_id=tenant.id,
            first_name="Juan",
            last_name="Pérez",
            document_number="12345678A",
            email="juan@example.com",
            phone="111",
            status="active",
        )
        person_other = Person(
            client_id=tenant.id,
            first_name="Ana",
            last_name="López",
            document_number="98765432B",
            email="ana@example.com",
            status="active",
        )
        db.session.add_all([person_portal, person_other])
        db.session.flush()

        employee_portal = Employee(
            client_id=tenant.id,
            company_id=company_owner.id,
            person_id=person_portal.id,
            full_name="Juan Pérez",
            status="active",
            start_date=date(2025, 1, 1),
        )
        employee_other = Employee(
            client_id=tenant.id,
            company_id=company_owner.id,
            person_id=person_other.id,
            full_name="Ana López",
            status="active",
            start_date=date(2025, 1, 1),
        )
        db.session.add_all([employee_portal, employee_other])
        db.session.flush()

        portal_user = User(
            client_id=tenant.id,
            email="portal@example.com",
            status="active",
            user_type="portal",
            person_id=person_portal.id,
            password_hash="x",
        )
        internal_user = User(
            client_id=tenant.id,
            email="internal@example.com",
            status="active",
            user_type="internal",
            password_hash="x",
        )
        db.session.add_all([portal_user, internal_user])
        db.session.flush()

        db.session.add_all(
            [
                Document(
                    client_id=tenant.id,
                    company_id=company_owner.id,
                    person_id=person_portal.id,
                    original_filename="doc_person.pdf",
                    storage_path="/tmp/a",
                    status="processed",
                    doc_type="dni",
                ),
                Document(
                    client_id=tenant.id,
                    company_id=company_owner.id,
                    employee_id=employee_portal.id,
                    original_filename="doc_employee.pdf",
                    storage_path="/tmp/b",
                    status="processed",
                    doc_type="payslip",
                ),
                Document(
                    client_id=tenant.id,
                    company_id=company_owner.id,
                    original_filename="doc_company_owner.pdf",
                    storage_path="/tmp/c",
                    status="processed",
                    doc_type="company_tax",
                ),
                Document(
                    client_id=tenant.id,
                    company_id=company_foreign.id,
                    original_filename="doc_company_foreign.pdf",
                    storage_path="/tmp/d",
                    status="processed",
                    doc_type="company_tax",
                ),
                Document(
                    client_id=tenant.id,
                    company_id=company_owner.id,
                    employee_id=employee_other.id,
                    original_filename="doc_other_employee.pdf",
                    storage_path="/tmp/e",
                    status="processed",
                ),
            ]
        )

        db.session.add_all(
            [
                Case(
                    client_id=tenant.id,
                    company_id=company_owner.id,
                    person_id=person_portal.id,
                    type="employment",
                    title="Caso personal",
                    status="in_progress",
                ),
                Case(
                    client_id=tenant.id,
                    company_id=company_owner.id,
                    type="tax",
                    title="Caso empresa owner",
                    status="open",
                ),
                Case(
                    client_id=tenant.id,
                    company_id=company_foreign.id,
                    type="tax",
                    title="Caso empresa ajena",
                    status="open",
                ),
            ]
        )

        db.session.add_all(
            [
                PersonCompanyRelation(
                    client_id=tenant.id,
                    person_id=person_portal.id,
                    company_id=company_owner.id,
                    relation_type="owner",
                    status="active",
                    start_date=date(2025, 1, 1),
                ),
                PersonCompanyRelation(
                    client_id=tenant.id,
                    person_id=person_other.id,
                    company_id=company_foreign.id,
                    relation_type="owner",
                    status="active",
                    start_date=date(2025, 1, 1),
                ),
            ]
        )

        db.session.commit()

        portal_token = create_access_token(portal_user.id, tenant.id)
        internal_token = create_access_token(internal_user.id, tenant.id)

        response = client.get("/portal", headers=_auth_header(portal_token))
        assert response.status_code == 200

        response = client.get("/portal", headers=_auth_header(internal_token))
        assert response.status_code == 403

        me = client.get("/portal/api/me", headers=_auth_header(portal_token))
        assert me.status_code == 200
        assert me.get_json()["person_id"] == person_portal.id

        summary = client.get("/portal/api/summary", headers=_auth_header(portal_token))
        assert summary.status_code == 200
        assert summary.get_json()["person_documents"] == 1
        assert summary.get_json()["employee_documents"] == 1
        assert summary.get_json()["company_documents"] == 4
        assert summary.get_json()["personal_cases"] == 1
        assert summary.get_json()["company_cases"] == 2
        assert summary.get_json()["companies_count"] == 1

        docs_person = client.get("/portal/api/documents?scope=person", headers=_auth_header(portal_token))
        assert docs_person.status_code == 200
        assert {item["file_name"] for item in docs_person.get_json()} == {"doc_person.pdf"}

        docs_employee = client.get("/portal/api/documents?scope=employee", headers=_auth_header(portal_token))
        assert docs_employee.status_code == 200
        assert {item["file_name"] for item in docs_employee.get_json()} == {"doc_employee.pdf"}

        docs_company = client.get("/portal/api/documents?scope=company", headers=_auth_header(portal_token))
        assert docs_company.status_code == 200
        assert {item["file_name"] for item in docs_company.get_json()} == {
            "doc_person.pdf",
            "doc_employee.pdf",
            "doc_company_owner.pdf",
            "doc_other_employee.pdf",
        }
        assert "doc_company_foreign.pdf" not in {item["file_name"] for item in docs_company.get_json()}

        all_docs = client.get("/portal/api/documents", headers=_auth_header(portal_token))
        assert all_docs.status_code == 200
        assert {item["file_name"] for item in all_docs.get_json()} == {
            "doc_person.pdf",
            "doc_employee.pdf",
            "doc_company_owner.pdf",
            "doc_other_employee.pdf",
        }

        cases_person = client.get("/portal/api/cases?scope=person", headers=_auth_header(portal_token))
        assert cases_person.status_code == 200
        assert {item["title"] for item in cases_person.get_json()} == {"Caso personal"}

        cases_company = client.get("/portal/api/cases?scope=company", headers=_auth_header(portal_token))
        assert cases_company.status_code == 200
        assert {item["title"] for item in cases_company.get_json()} == {
            "Caso personal",
            "Caso empresa owner",
        }

        companies = client.get("/portal/api/companies", headers=_auth_header(portal_token))
        assert companies.status_code == 200
        assert len(companies.get_json()) == 1
        assert companies.get_json()[0]["company_name"] == "Empresa Owner"

        company_detail = client.get(
            f"/portal/api/companies/{company_owner.id}",
            headers=_auth_header(portal_token),
        )
        assert company_detail.status_code == 200

        forbidden_detail = client.get(
            f"/portal/api/companies/{company_foreign.id}",
            headers=_auth_header(portal_token),
        )
        assert forbidden_detail.status_code == 403

        company_docs = client.get(
            f"/portal/api/companies/{company_owner.id}/documents",
            headers=_auth_header(portal_token),
        )
        assert company_docs.status_code == 200
        assert {item["file_name"] for item in company_docs.get_json()} == {
            "doc_person.pdf",
            "doc_employee.pdf",
            "doc_company_owner.pdf",
            "doc_other_employee.pdf",
        }

        company_cases = client.get(
            f"/portal/api/companies/{company_owner.id}/cases",
            headers=_auth_header(portal_token),
        )
        assert company_cases.status_code == 200
        assert {item["title"] for item in company_cases.get_json()} == {
            "Caso personal",
            "Caso empresa owner",
        }

        foreign_company_docs = client.get(
            f"/portal/api/companies/{company_foreign.id}/documents",
            headers=_auth_header(portal_token),
        )
        assert foreign_company_docs.status_code == 403

