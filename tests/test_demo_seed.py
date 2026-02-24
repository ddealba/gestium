from app.cli import seed_demo
from app.extensions import db
from app.models.case import Case
from app.models.case_event import CaseEvent
from app.models.client import Client
from app.models.company import Company
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.models.employee import Employee


def test_seed_demo_creates_domain_data_and_is_idempotent(app):
    with app.app_context():
        db.create_all()

        seed_demo()

        tenant_a = Client.query.filter_by(name="Tenant A").one()
        assert Company.query.filter_by(client_id=tenant_a.id).count() >= 2
        assert Employee.query.filter_by(client_id=tenant_a.id).count() >= 3
        assert Case.query.filter_by(client_id=tenant_a.id).count() >= 3
        assert Document.query.filter_by(client_id=tenant_a.id).count() >= 3
        assert DocumentExtraction.query.filter_by(client_id=tenant_a.id).count() >= 3
        assert CaseEvent.query.filter_by(client_id=tenant_a.id).count() >= 6

        employees_count = Employee.query.count()
        cases_count = Case.query.count()
        documents_count = Document.query.count()
        extractions_count = DocumentExtraction.query.count()
        events_count = CaseEvent.query.count()

        seed_demo()

        assert Employee.query.count() == employees_count
        assert Case.query.count() == cases_count
        assert Document.query.count() == documents_count
        assert DocumentExtraction.query.count() == extractions_count
        assert CaseEvent.query.count() == events_count

        db.drop_all()
