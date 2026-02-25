"""Application CLI commands."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import click
from flask import Flask, current_app

from app.extensions import db
from app.common.access_levels import AccessLevel
from app.models.case import Case
from app.models.case_event import CaseEvent
from app.models.client import Client
from app.models.company import Company
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.models.employee import Employee
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.user_company_access_repository import UserCompanyAccessRepository
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService

RBAC_PERMISSIONS: dict[str, str] = {
    "tenant.profile.read": "Read tenant profile",
    "tenant.profile.write": "Update tenant profile",
    "tenant.users.invite": "Invite tenant users",
    "tenant.users.manage": "Manage tenant users",
    "tenant.user.read": "Read tenant users",
    "tenant.user.invite": "Invite tenant users",
    "tenant.user.manage": "Manage tenant users",
    "tenant.role.read": "Read tenant roles",
    "company.read": "Read companies",
    "tenant.company.read": "Read tenant companies",
    "company.write": "Manage companies",
    "acl.read": "Read company ACL entries",
    "acl.manage": "Manage company ACL entries",
    "employee.read": "Read employees",
    "employee.write": "Manage employees",
    "case.read": "Read cases",
    "case.write": "Manage cases",
    "case.assign": "Assign cases",
    "case.event.write": "Write case events",
    "document.read": "Read documents",
    "document.write": "Manage document status",
    "document.upload": "Upload documents",
    "document.classify": "Classify documents",
    "document.extraction.read": "Read document extractions",
    "document.extraction.write": "Manage document extractions",
    "audit.read": "Read audit logs",
    "platform.clients.manage": "Manage platform clients",
    "platform.metrics.read": "Read platform metrics",
}

RBAC_ROLE_PERMISSIONS: dict[str, list[str]] = {
    "Super Admin": ["*"],
    "Admin Cliente": [
        "tenant.profile.read",
        "tenant.profile.write",
        "tenant.users.invite",
        "tenant.users.manage",
        "tenant.user.read",
        "tenant.user.invite",
        "tenant.user.manage",
        "tenant.role.read",
        "company.read",
        "tenant.company.read",
        "company.write",
        "acl.read",
        "acl.manage",
        "employee.read",
        "employee.write",
        "case.read",
        "case.write",
        "case.assign",
        "case.event.write",
        "document.read",
        "document.write",
        "document.upload",
        "document.classify",
        "document.extraction.read",
        "document.extraction.write",
        "audit.read",
    ],
    "Asesor": [
        "company.read",
        "tenant.company.read",
        "employee.read",
        "case.read",
        "case.write",
        "case.event.write",
        "document.read",
        "document.write",
        "document.upload",
        "document.classify",
        "document.extraction.read",
    ],
    "Operativo": [
        "company.read",
        "tenant.company.read",
        "employee.read",
        "case.read",
        "case.event.write",
        "document.read",
        "document.write",
        "document.upload",
    ],
}


def register_cli(app: Flask) -> None:
    """Register CLI commands on the Flask app."""

    @app.cli.command("seed")
    @click.option(
        "--scenario",
        type=click.Choice(["default", "smoke", "demo"], case_sensitive=False),
        default="default",
        show_default=True,
        help="Seed scenario to run.",
    )
    @click.option(
        "--allow-production",
        is_flag=True,
        help="Allow seeding outside development.",
    )
    def seed(scenario: str, allow_production: bool) -> None:
        """Seed the database with initial data."""
        _ensure_seed_allowed(allow_production)
        normalized_scenario = scenario.lower()
        if normalized_scenario == "smoke":
            seed_smoke()
        elif normalized_scenario == "demo":
            seed_demo()
        else:
            seed_default_client()
            seed_rbac()

    @app.cli.command("seed_clients")
    @click.option(
        "--allow-production",
        is_flag=True,
        help="Allow seeding outside development.",
    )
    def seed_clients(allow_production: bool) -> None:
        """Seed the database with initial client data."""
        _ensure_seed_allowed(allow_production)
        seed_default_client()

    @app.cli.command("seed_rbac")
    @click.option(
        "--allow-production",
        is_flag=True,
        help="Allow seeding outside development.",
    )
    def seed_rbac_command(allow_production: bool) -> None:
        """Seed the database with RBAC permissions and roles."""
        _ensure_seed_allowed(allow_production)
        seed_rbac()

    @app.cli.command("seed_smoke")
    @click.option(
        "--allow-production",
        is_flag=True,
        help="Allow seeding outside development.",
    )
    def seed_smoke_command(allow_production: bool) -> None:
        """Seed the database with the deterministic smoke scenario."""
        _ensure_seed_allowed(allow_production)
        seed_smoke()


def seed_default_client() -> None:
    """Create the default client if it does not exist."""
    existing_client = Client.query.filter_by(name="Default Client").first()
    if existing_client:
        click.echo("Default Client already exists. Skipping.")
        return

    client = Client(name="Default Client", status="active", plan="mvp")
    db.session.add(client)
    db.session.commit()
    click.echo("Default Client created.")


def seed_rbac() -> None:
    """Seed base permissions and roles for the MVP."""
    permissions_by_code: dict[str, Permission] = {}
    for code, description in RBAC_PERMISSIONS.items():
        permission = Permission.query.filter_by(code=code).first()
        if not permission:
            permission = Permission(code=code, description=description)
            db.session.add(permission)
        permissions_by_code[code] = permission
    db.session.flush()

    all_codes = set(permissions_by_code.keys())

    super_admin = Role.query.filter_by(name="Super Admin", scope="platform", client_id=None).first()
    if not super_admin:
        super_admin = Role(name="Super Admin", scope="platform", client_id=None)
        db.session.add(super_admin)
        db.session.flush()

    _assign_role_permissions(super_admin, all_codes, permissions_by_code)

    clients = Client.query.filter_by(status="active").all()
    for client in clients:
        for role_name in ("Admin Cliente", "Asesor", "Operativo"):
            role = Role.query.filter_by(
                name=role_name,
                scope="tenant",
                client_id=client.id,
            ).first()
            if not role:
                role = Role(name=role_name, scope="tenant", client_id=client.id)
                db.session.add(role)
                db.session.flush()
            _assign_role_permissions(
                role,
                set(RBAC_ROLE_PERMISSIONS[role_name]),
                permissions_by_code,
            )

    db.session.commit()
    click.echo("RBAC permissions and roles seeded.")


SMOKE_TENANT_A_ID = "1a8b9d30-7c7c-4c05-9e1c-2c7a7a96c1a1"
SMOKE_TENANT_B_ID = "2b9c0e41-8d8d-4d16-af2d-3d8b8bb7d2b2"
SMOKE_COMPANY_A1_ID = "3c0d1f52-9e9e-4e27-b03e-4e9c9cc8e3c3"
SMOKE_COMPANY_A2_ID = "4d1e2053-afaf-4f38-c14f-5fadadd9f4d4"
SMOKE_COMPANY_B1_ID = "5e2f3164-b0b0-5049-d250-60bebeea05e5"


def seed_smoke() -> dict[str, Client | Company | User]:
    """Seed a deterministic smoke scenario."""
    click.echo("Seeding smoke scenario...")
    client_a = _get_or_create_client("Tenant A", SMOKE_TENANT_A_ID)
    client_b = _get_or_create_client("Tenant B", SMOKE_TENANT_B_ID)

    seed_rbac()

    user_service = UserService(UserRepository())
    role_repository = RoleRepository()
    access_repository = UserCompanyAccessRepository()

    admin_a = _get_or_create_user(client_a, "adminA@test.com", "Passw0rd!", user_service)
    viewer_a = _get_or_create_user(client_a, "viewerA@test.com", "Passw0rd!", user_service)
    admin_b = _get_or_create_user(client_b, "adminB@test.com", "Passw0rd!", user_service)

    admin_role_a = _get_or_create_role(client_a, "Admin Cliente", role_repository)
    operative_role_a = _get_or_create_role(client_a, "Operativo", role_repository)
    admin_role_b = _get_or_create_role(client_b, "Admin Cliente", role_repository)

    _assign_role(admin_a, admin_role_a)
    _assign_role(viewer_a, operative_role_a)
    _assign_role(admin_b, admin_role_b)

    company_a1 = _get_or_create_company(client_a, "A1", "A1", SMOKE_COMPANY_A1_ID)
    company_a2 = _get_or_create_company(client_a, "A2", "A2", SMOKE_COMPANY_A2_ID)
    company_b1 = _get_or_create_company(client_b, "B1", "B1", SMOKE_COMPANY_B1_ID)

    _upsert_company_access(
        access_repository,
        admin_a,
        company_a1,
        AccessLevel.admin.value,
    )
    _upsert_company_access(
        access_repository,
        admin_a,
        company_a2,
        AccessLevel.admin.value,
    )
    _upsert_company_access(
        access_repository,
        viewer_a,
        company_a1,
        AccessLevel.viewer.value,
    )
    _upsert_company_access(
        access_repository,
        admin_b,
        company_b1,
        AccessLevel.admin.value,
    )

    db.session.commit()
    click.echo("Smoke scenario seeded.")
    click.echo("")
    click.echo("Smoke seed details:")
    click.echo(f"Tenant A ID: {client_a.id}")
    click.echo(f"Tenant B ID: {client_b.id}")
    click.echo(f"Company A1 ID: {company_a1.id}")
    click.echo(f"Company A2 ID: {company_a2.id}")
    click.echo(f"Company B1 ID: {company_b1.id}")
    click.echo("Credentials:")
    click.echo("  adminA@test.com / Passw0rd!")
    click.echo("  viewerA@test.com / Passw0rd!")
    click.echo("  adminB@test.com / Passw0rd!")

    return {
        "client_a": client_a,
        "client_b": client_b,
        "company_a1": company_a1,
        "company_a2": company_a2,
        "company_b1": company_b1,
        "admin_a": admin_a,
        "viewer_a": viewer_a,
        "admin_b": admin_b,
    }


def seed_demo() -> None:
    """Seed deterministic data to exercise all major app capabilities."""
    click.echo("Seeding demo scenario...")
    smoke_data = seed_smoke()

    client_a = smoke_data["client_a"]
    company_a1 = smoke_data["company_a1"]
    company_a2 = smoke_data["company_a2"]
    admin_a = smoke_data["admin_a"]
    viewer_a = smoke_data["viewer_a"]

    _seed_demo_employees(client_a, company_a1, company_a2)
    seeded_cases = _seed_demo_cases(client_a, company_a1, company_a2, admin_a, viewer_a)
    _seed_demo_documents(client_a, admin_a, seeded_cases)

    db.session.commit()
    click.echo("Demo scenario seeded.")


def _seed_demo_employees(client: Client, company_a1: Company, company_a2: Company) -> None:
    employees = [
        {
            "company": company_a1,
            "full_name": "María Gómez",
            "employee_ref": "A1-EMP-001",
            "status": "active",
            "start_date": date(2021, 5, 10),
            "end_date": None,
        },
        {
            "company": company_a1,
            "full_name": "Carlos Pérez",
            "employee_ref": "A1-EMP-002",
            "status": "terminated",
            "start_date": date(2020, 3, 1),
            "end_date": date(2024, 8, 30),
        },
        {
            "company": company_a2,
            "full_name": "Lucía Torres",
            "employee_ref": "A2-EMP-001",
            "status": "active",
            "start_date": date(2022, 11, 15),
            "end_date": None,
        },
    ]

    for payload in employees:
        employee = Employee.query.filter_by(
            client_id=client.id,
            company_id=payload["company"].id,
            employee_ref=payload["employee_ref"],
        ).first()
        if employee is None:
            employee = Employee(
                client_id=client.id,
                company_id=payload["company"].id,
                full_name=payload["full_name"],
                employee_ref=payload["employee_ref"],
                status=payload["status"],
                start_date=payload["start_date"],
                end_date=payload["end_date"],
            )
            db.session.add(employee)
            click.echo(f"Created employee {payload['employee_ref']}.")
        else:
            click.echo(f"Reused employee {payload['employee_ref']}.")


def _seed_demo_cases(
    client: Client,
    company_a1: Company,
    company_a2: Company,
    admin_a: User,
    viewer_a: User,
) -> list[Case]:
    today = date.today()
    cases = [
        {
            "company": company_a1,
            "type": "laboral",
            "title": "Revisión de contrato colectivo",
            "description": "Analizar cláusulas y riesgos para renovación.",
            "status": "in_progress",
            "responsible": admin_a,
            "due_date": today + timedelta(days=15),
        },
        {
            "company": company_a1,
            "type": "inspección",
            "title": "Inspección de seguridad e higiene",
            "description": "Preparar documentación para visita de autoridad.",
            "status": "waiting",
            "responsible": viewer_a,
            "due_date": today + timedelta(days=7),
        },
        {
            "company": company_a2,
            "type": "nómina",
            "title": "Ajuste extraordinario de nómina",
            "description": "Regularización de percepciones variables.",
            "status": "open",
            "responsible": admin_a,
            "due_date": today + timedelta(days=21),
        },
    ]

    seeded_cases: list[Case] = []
    for payload in cases:
        record = Case.query.filter_by(
            client_id=client.id,
            company_id=payload["company"].id,
            title=payload["title"],
        ).first()
        if record is None:
            record = Case(
                client_id=client.id,
                company_id=payload["company"].id,
                type=payload["type"],
                title=payload["title"],
                description=payload["description"],
                status=payload["status"],
                responsible_user_id=payload["responsible"].id,
                due_date=payload["due_date"],
            )
            db.session.add(record)
            db.session.flush()
            click.echo(f"Created case '{payload['title']}'.")
        else:
            click.echo(f"Reused case '{payload['title']}'.")
        seeded_cases.append(record)

        _upsert_case_event(
            client_id=client.id,
            company_id=payload["company"].id,
            case_id=record.id,
            actor_user_id=payload["responsible"].id,
            event_type="assignment",
            payload={"assigned_to": payload["responsible"].email, "source": "demo-seed"},
        )
        _upsert_case_event(
            client_id=client.id,
            company_id=payload["company"].id,
            case_id=record.id,
            actor_user_id=payload["responsible"].id,
            event_type="comment",
            payload={"message": "Caso generado automáticamente para demo."},
        )

    return seeded_cases


def _seed_demo_documents(client: Client, admin_user: User, seeded_cases: list[Case]) -> None:
    for case_record in seeded_cases:
        filename = f"{case_record.title.lower().replace(' ', '_')}.pdf"
        storage_path = f"demo/{client.id}/{case_record.company_id}/{case_record.id}/{filename}"
        document = Document.query.filter_by(
            client_id=client.id,
            case_id=case_record.id,
            original_filename=filename,
        ).first()
        if document is None:
            document = Document(
                client_id=client.id,
                company_id=case_record.company_id,
                case_id=case_record.id,
                uploaded_by_user_id=admin_user.id,
                original_filename=filename,
                content_type="application/pdf",
                storage_path=storage_path,
                size_bytes=248000,
                doc_type="expediente",
                status="processed",
            )
            db.session.add(document)
            db.session.flush()
            click.echo(f"Created document {filename}.")
        else:
            click.echo(f"Reused document {filename}.")

        extraction = DocumentExtraction.query.filter_by(
            client_id=client.id,
            document_id=document.id,
            schema_version="v1.demo",
        ).first()
        if extraction is None:
            extraction = DocumentExtraction(
                client_id=client.id,
                document_id=document.id,
                company_id=case_record.company_id,
                case_id=case_record.id,
                created_by_user_id=admin_user.id,
                provider="demo",
                model_name="seed-generator",
                schema_version="v1.demo",
                extracted_json={
                    "case_title": case_record.title,
                    "summary": "Extracción simulada para entorno demo.",
                    "tags": ["demo", case_record.type, case_record.status],
                },
                confidence=0.91,
                status="success",
            )
            db.session.add(extraction)
            click.echo(f"Created extraction for {filename}.")
        else:
            click.echo(f"Reused extraction for {filename}.")


def _upsert_case_event(
    client_id: str,
    company_id: str,
    case_id: str,
    actor_user_id: str,
    event_type: str,
    payload: dict,
) -> None:
    event = CaseEvent.query.filter_by(
        client_id=client_id,
        case_id=case_id,
        event_type=event_type,
    ).first()
    if event is None:
        event = CaseEvent(
            client_id=client_id,
            company_id=company_id,
            case_id=case_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            payload=payload,
        )
        db.session.add(event)
        click.echo(f"Created case event {event_type} for case {case_id}.")
    else:
        click.echo(f"Reused case event {event_type} for case {case_id}.")


def _ensure_seed_allowed(allow_production: bool) -> None:
    env = current_app.config.get("ENV", "development")
    if env != "development" and not allow_production:
        raise click.ClickException(
            "Seeding is only allowed in development. Use --allow-production to override."
        )


def _get_or_create_client(name: str, client_id: str | None = None) -> Client:
    client = None
    if client_id:
        client = Client.query.filter_by(id=client_id).first()
    if not client:
        client = Client.query.filter_by(name=name).first()
    if not client:
        client = Client(id=client_id or str(uuid.uuid4()), name=name, status="active", plan="smoke")
        db.session.add(client)
        db.session.flush()
        click.echo(f"Created client {name}.")
        return client

    updated = False
    if client.status != "active":
        client.status = "active"
        updated = True
    if updated:
        db.session.add(client)
        click.echo(f"Updated client {name}.")
    else:
        click.echo(f"Reused client {name}.")
    return client


def _get_or_create_company(
    client: Client, name: str, tax_id: str, company_id: str | None = None
) -> Company:
    company = None
    if company_id:
        company = Company.query.filter_by(id=company_id).first()
    if not company:
        company = Company.query.filter_by(client_id=client.id, tax_id=tax_id).first()
    if not company:
        company = Company(
            id=company_id or str(uuid.uuid4()),
            client_id=client.id,
            name=name,
            tax_id=tax_id,
            status="active",
        )
        db.session.add(company)
        db.session.flush()
        click.echo(f"Created company {name} for {client.name}.")
        return company

    updated = False
    if company.name != name:
        company.name = name
        updated = True
    if company.status != "active":
        company.status = "active"
        updated = True
    if updated:
        db.session.add(company)
        click.echo(f"Updated company {name} for {client.name}.")
    else:
        click.echo(f"Reused company {name} for {client.name}.")
    return company


def _get_or_create_user(client: Client, email: str, password: str, user_service: UserService) -> User:
    normalized_email = user_service.normalize_email(email)
    repository = user_service.repository
    user = repository.get_by_email(normalized_email, client.id)
    if not user:
        user = user_service.create_invited_user(client.id, normalized_email)
        click.echo(f"Created user {normalized_email} for {client.name}.")
    else:
        click.echo(f"Reused user {normalized_email} for {client.name}.")

    activated = user_service.activate_user(user.id, client.id, password)
    if activated is not None:
        user = activated
        click.echo(f"Activated user {normalized_email} for {client.name}.")
    return user


def _get_or_create_role(client: Client, name: str, repository: RoleRepository) -> Role:
    role = repository.get_by_name(name, "tenant", client.id)
    if role:
        click.echo(f"Reused role {name} for {client.name}.")
        return role
    role = Role(name=name, scope="tenant", client_id=client.id)
    db.session.add(role)
    db.session.flush()
    click.echo(f"Created role {name} for {client.name}.")
    return role


def _assign_role(user: User, role: Role) -> None:
    if role in user.roles:
        click.echo(f"Role {role.name} already assigned to {user.email}.")
        return
    user.roles.append(role)
    db.session.add(user)
    click.echo(f"Assigned role {role.name} to {user.email}.")


def _upsert_company_access(
    repository: UserCompanyAccessRepository,
    user: User,
    company: Company,
    access_level: str,
) -> None:
    existing = repository.get_user_access(user.id, company.id, company.client_id)
    if existing is None:
        repository.upsert_access(user.id, company.id, company.client_id, access_level)
        click.echo(
            f"Created {access_level} access for {user.email} on {company.name} ({company.client_id})."
        )
    elif existing.access_level != access_level:
        repository.upsert_access(user.id, company.id, company.client_id, access_level)
        click.echo(
            f"Updated access for {user.email} on {company.name} to {access_level} ({company.client_id})."
        )
    else:
        click.echo(
            f"Reused access for {user.email} on {company.name} ({company.client_id})."
        )


def _assign_role_permissions(
    role: Role,
    requested_codes: set[str],
    permissions_by_code: dict[str, Permission],
) -> None:
    if "*" in requested_codes:
        requested_codes = set(permissions_by_code.keys())
    existing_codes = {permission.code for permission in role.permissions}
    for code in sorted(requested_codes - existing_codes):
        role.permissions.append(permissions_by_code[code])
