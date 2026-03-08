from datetime import date

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


def test_portal_access_and_data_isolation(client, app):
    with app.app_context():
        db.create_all()

        tenant_a = Client(name="Tenant A", status="active")
        tenant_b = Client(name="Tenant B", status="active")
        db.session.add_all([tenant_a, tenant_b])
        db.session.flush()

        company_a = Company(client_id=tenant_a.id, name="Empresa X", tax_id="AX1", status="active")
        company_b = Company(client_id=tenant_b.id, name="Empresa Y", tax_id="BY1", status="active")
        db.session.add_all([company_a, company_b])
        db.session.flush()

        person_portal = Person(
            client_id=tenant_a.id,
            first_name="Juan",
            last_name="Pérez",
            document_number="12345678A",
            email="juan@example.com",
            phone="111",
            status="active",
        )
        person_other = Person(
            client_id=tenant_a.id,
            first_name="Ana",
            last_name="López",
            document_number="98765432B",
            email="ana@example.com",
            status="active",
        )
        person_other_tenant = Person(
            client_id=tenant_b.id,
            first_name="Mike",
            last_name="Stone",
            document_number="ZZZ111",
            email="mike@example.com",
            status="active",
        )
        db.session.add_all([person_portal, person_other, person_other_tenant])
        db.session.flush()

        employee_portal = Employee(
            client_id=tenant_a.id,
            company_id=company_a.id,
            person_id=person_portal.id,
            full_name="Juan Pérez",
            status="active",
            start_date=date(2025, 1, 1),
        )
        db.session.add(employee_portal)
        db.session.flush()

        portal_user = User(
            client_id=tenant_a.id,
            email="portal@example.com",
            status="active",
            user_type="portal",
            person_id=person_portal.id,
            password_hash="x",
        )
        internal_user = User(
            client_id=tenant_a.id,
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
                    client_id=tenant_a.id,
                    company_id=company_a.id,
                    person_id=person_portal.id,
                    original_filename="doc_person.pdf",
                    storage_path="/tmp/a",
                    status="processed",
                    doc_type="payslip",
                ),
                Document(
                    client_id=tenant_a.id,
                    company_id=company_a.id,
                    employee_id=employee_portal.id,
                    original_filename="doc_employee.pdf",
                    storage_path="/tmp/b",
                    status="processed",
                    doc_type="contract",
                ),
                Document(
                    client_id=tenant_a.id,
                    company_id=company_a.id,
                    person_id=person_other.id,
                    original_filename="doc_other.pdf",
                    storage_path="/tmp/c",
                    status="processed",
                ),
                Document(
                    client_id=tenant_b.id,
                    company_id=company_b.id,
                    person_id=person_other_tenant.id,
                    original_filename="doc_tenant_b.pdf",
                    storage_path="/tmp/d",
                    status="processed",
                ),
            ]
        )

        db.session.add_all(
            [
                Case(
                    client_id=tenant_a.id,
                    company_id=company_a.id,
                    person_id=person_portal.id,
                    type="employment",
                    title="Alta de empleado",
                    status="in_progress",
                ),
                Case(
                    client_id=tenant_a.id,
                    company_id=company_a.id,
                    person_id=person_other.id,
                    type="employment",
                    title="Otro caso",
                    status="open",
                ),
                Case(
                    client_id=tenant_b.id,
                    company_id=company_b.id,
                    person_id=person_other_tenant.id,
                    type="tax",
                    title="Caso B",
                    status="open",
                ),
            ]
        )

        db.session.add_all(
            [
                PersonCompanyRelation(
                    client_id=tenant_a.id,
                    person_id=person_portal.id,
                    company_id=company_a.id,
                    relation_type="employee",
                    status="active",
                    start_date=date(2025, 1, 1),
                ),
                PersonCompanyRelation(
                    client_id=tenant_a.id,
                    person_id=person_other.id,
                    company_id=company_a.id,
                    relation_type="owner",
                    status="active",
                    start_date=date(2025, 1, 1),
                ),
            ]
        )

        db.session.commit()

        portal_token = create_access_token(portal_user.id, tenant_a.id)
        internal_token = create_access_token(internal_user.id, tenant_a.id)

        response = client.get("/portal", headers=_auth_header(portal_token))
        assert response.status_code == 200

        response = client.get("/app/companies", headers=_auth_header(portal_token))
        assert response.status_code == 403

        response = client.get("/portal", headers=_auth_header(internal_token))
        assert response.status_code == 403

        me = client.get("/portal/api/me", headers=_auth_header(portal_token))
        assert me.status_code == 200
        assert me.get_json()["person_id"] == person_portal.id

        docs = client.get("/portal/api/my-documents", headers=_auth_header(portal_token))
        assert docs.status_code == 200
        doc_names = {item["file_name"] for item in docs.get_json()}
        assert doc_names == {"doc_person.pdf", "doc_employee.pdf"}

        cases = client.get("/portal/api/my-cases", headers=_auth_header(portal_token))
        assert cases.status_code == 200
        case_titles = {item["title"] for item in cases.get_json()}
        assert case_titles == {"Alta de empleado"}

        companies = client.get("/portal/api/my-companies", headers=_auth_header(portal_token))
        assert companies.status_code == 200
        payload = companies.get_json()
        assert len(payload) == 1
        assert payload[0]["company_name"] == "Empresa X"

        db.drop_all()
