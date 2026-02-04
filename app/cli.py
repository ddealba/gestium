"""Application CLI commands."""

from __future__ import annotations

import click
from flask import Flask

from app.extensions import db
from app.models.client import Client
from app.models.permission import Permission
from app.models.role import Role

RBAC_PERMISSIONS: dict[str, str] = {
    "tenant.profile.read": "Read tenant profile",
    "tenant.profile.write": "Update tenant profile",
    "tenant.users.invite": "Invite tenant users",
    "tenant.users.manage": "Manage tenant users",
    "company.read": "Read companies",
    "company.write": "Manage companies",
    "employee.read": "Read employees",
    "employee.write": "Manage employees",
    "case.read": "Read cases",
    "case.write": "Manage cases",
    "case.assign": "Assign cases",
    "case.event.write": "Write case events",
    "document.read": "Read documents",
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
        "company.read",
        "company.write",
        "employee.read",
        "employee.write",
        "case.read",
        "case.write",
        "case.assign",
        "case.event.write",
        "document.read",
        "document.upload",
        "document.classify",
        "document.extraction.read",
        "document.extraction.write",
        "audit.read",
    ],
    "Asesor": [
        "company.read",
        "employee.read",
        "case.read",
        "case.write",
        "case.event.write",
        "document.read",
        "document.upload",
        "document.classify",
        "document.extraction.read",
    ],
    "Operativo": [
        "company.read",
        "employee.read",
        "case.read",
        "case.event.write",
        "document.read",
        "document.upload",
    ],
}


def register_cli(app: Flask) -> None:
    """Register CLI commands on the Flask app."""

    @app.cli.command("seed")
    def seed() -> None:
        """Seed the database with initial data."""
        seed_default_client()
        seed_rbac()

    @app.cli.command("seed_clients")
    def seed_clients() -> None:
        """Seed the database with initial client data."""
        seed_default_client()

    @app.cli.command("seed_rbac")
    def seed_rbac_command() -> None:
        """Seed the database with RBAC permissions and roles."""
        seed_rbac()


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
