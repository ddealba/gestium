from app.cli import seed_rbac
from app.extensions import db
from app.models.client import Client
from app.models.permission import Permission
from app.models.role import Role


def test_seed_rbac_creates_permissions_and_roles(app):
    with app.app_context():
        db.create_all()
        active_client = Client(name="Active Client", status="active")
        inactive_client = Client(name="Inactive Client", status="suspended")
        db.session.add_all([active_client, inactive_client])
        db.session.commit()

        seed_rbac()

        expected_permissions = {
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
            "platform.clients.manage",
            "platform.metrics.read",
        }
        stored_permissions = {permission.code for permission in Permission.query.all()}
        assert expected_permissions == stored_permissions

        super_admin = Role.query.filter_by(name="Super Admin", scope="platform", client_id=None).one()
        assert {permission.code for permission in super_admin.permissions} == expected_permissions

        admin_role = Role.query.filter_by(
            name="Admin Cliente",
            scope="tenant",
            client_id=active_client.id,
        ).one()
        assert "audit.read" in {permission.code for permission in admin_role.permissions}

        advisor_role = Role.query.filter_by(
            name="Asesor",
            scope="tenant",
            client_id=active_client.id,
        ).one()
        advisor_codes = {permission.code for permission in advisor_role.permissions}
        assert "case.write" in advisor_codes
        assert "audit.read" not in advisor_codes

        operator_role = Role.query.filter_by(
            name="Operativo",
            scope="tenant",
            client_id=active_client.id,
        ).one()
        operator_codes = {permission.code for permission in operator_role.permissions}
        assert "document.upload" in operator_codes
        assert "document.write" in operator_codes

        assert (
            Role.query.filter_by(
                name="Admin Cliente",
                scope="tenant",
                client_id=inactive_client.id,
            ).first()
            is None
        )

        permissions_count = Permission.query.count()
        roles_count = Role.query.count()

        seed_rbac()

        assert Permission.query.count() == permissions_count
        assert Role.query.count() == roles_count
        db.drop_all()
