"""Initial base schema with multi-tenancy and RLS.

- tenants
- users
- roles
- permissions
- user_roles
- role_permissions
- org_units
- audit_log
- notifications

Also creates helper function set_tenant_id(uuid) to set the app.tenant_id GUC.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9f0b6b3a9a01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # Helper function to set tenant in the current session
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_tenant_id(p_tenant_id uuid)
        RETURNS void AS $$
        BEGIN
            PERFORM set_config('app.tenant_id', p_tenant_id::text, false);
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Tenants
    op.create_table(
        "tenants",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=sa.text("current_setting('app.tenant_id', true)::uuid")),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=True),
        sa.Column("hashed_password", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_superadmin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    # Roles
    op.create_table(
        "roles",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=sa.text("current_setting('app.tenant_id', true)::uuid")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_roles_tenant_name"),
    )

    # Permissions
    op.create_table(
        "permissions",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=sa.text("current_setting('app.tenant_id', true)::uuid")),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_permissions_tenant_code"),
    )

    # Association: user_roles
    op.create_table(
        "user_roles",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=sa.text("current_setting('app.tenant_id', true)::uuid")),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "user_id", "role_id", name="uq_user_roles_tenant_user_role"),
    )

    # Association: role_permissions
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=sa.text("current_setting('app.tenant_id', true)::uuid")),
        sa.Column("role_id", sa.UUID(), nullable=False),
        sa.Column("permission_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "role_id", "permission_id", name="uq_role_permissions_tenant_role_permission"),
    )

    # Org Units
    op.create_table(
        "org_units",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=sa.text("current_setting('app.tenant_id', true)::uuid")),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("path", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["org_units.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_org_units_tenant_name"),
    )

    # Audit Log
    op.create_table(
        "audit_log",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=sa.text("current_setting('app.tenant_id', true)::uuid")),
        sa.Column("actor_user_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=True),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("metadata", sa.JSON(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.Index("ix_audit_log_tenant_created_at", "tenant_id", "created_at"),
    )

    # Notifications
    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=sa.text("current_setting('app.tenant_id', true)::uuid")),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.Index("ix_notifications_tenant_created_at", "tenant_id", "created_at"),
    )

    # Enable RLS and add policies
    # Tenants table
    op.execute("ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_row_access ON tenants
        USING (id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (id = current_setting('app.tenant_id', true)::uuid);
        """
    )

    # Tenant-scoped tables
    tenant_scoped_tables = [
        "users",
        "roles",
        "permissions",
        "user_roles",
        "role_permissions",
        "org_units",
        "audit_log",
        "notifications",
    ]
    for tbl in tenant_scoped_tables:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY {tbl}_tenant_isolation ON {tbl}
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
            """
        )


def downgrade() -> None:
    # Drop RLS policies
    op.execute("DROP POLICY IF EXISTS tenant_row_access ON tenants;")
    for tbl in [
        "users",
        "roles",
        "permissions",
        "user_roles",
        "role_permissions",
        "org_units",
        "audit_log",
        "notifications",
    ]:
        op.execute(f"DROP POLICY IF EXISTS {tbl}_tenant_isolation ON {tbl};")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY;")

    op.execute("ALTER TABLE tenants DISABLE ROW LEVEL SECURITY;")

    # Drop tables in reverse dependency order
    op.drop_table("notifications")
    op.drop_table("audit_log")
    op.drop_table("org_units")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("tenants")

    # Helper function
    op.execute("DROP FUNCTION IF EXISTS set_tenant_id(uuid);")

    # Extensions are left installed (safe and idempotent); no drop needed.
