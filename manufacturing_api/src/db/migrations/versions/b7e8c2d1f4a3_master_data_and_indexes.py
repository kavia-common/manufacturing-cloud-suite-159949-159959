"""Add master-data tables (UoM, items, work centers, routing/BOM) and performance indexes.

Also creates broad indexes for tenant_id, status, common FKs, and timestamp fields
across tenant-scoped tables to improve query performance.

Tables:
- units_of_measure
- items
- work_centers
- routings
- routing_operations
- boms
- bom_lines
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b7e8c2d1f4a3"
down_revision: Union[str, None] = "a2e4f7c1b8d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_DEFAULT = sa.text("current_setting('app.tenant_id', true)::uuid")
UUID_DEFAULT = sa.text("uuid_generate_v4()")
NOW = sa.text("now()")
JSONB_EMPTY = sa.text("'{}'::jsonb")


def _enable_rls_with_policy(table: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
    op.execute(
        f"""
        CREATE POLICY {table}_tenant_isolation ON {table}
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
        WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);
        """
    )


def upgrade() -> None:
    # Master data: Units of Measure
    op.create_table(
        "units_of_measure",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_uom_tenant_code"),
        sa.Index("ix_uom_tenant_code", "tenant_id", "code"),
    )

    # Items
    op.create_table(
        "items",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("sku", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_uom_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["default_uom_id"], ["units_of_measure.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "sku", name="uq_items_tenant_sku"),
        sa.Index("ix_items_tenant_sku", "tenant_id", "sku"),
    )

    # Work Centers
    op.create_table(
        "work_centers",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("asset_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_work_centers_tenant_code"),
        sa.Index("ix_work_centers_tenant_code", "tenant_id", "code"),
    )

    # Routings and operations
    op.create_table(
        "routings",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("item_id", sa.UUID(), nullable=True),
        sa.Column("revision", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_routings_tenant_code"),
        sa.Index("ix_routings_tenant_code", "tenant_id", "code"),
    )

    op.create_table(
        "routing_operations",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("routing_id", sa.UUID(), nullable=False),
        sa.Column("seq_no", sa.Integer(), nullable=False),
        sa.Column("operation_code", sa.Text(), nullable=True),
        sa.Column("work_center_id", sa.UUID(), nullable=True),
        sa.Column("standard_time_minutes", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["routing_id"], ["routings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_center_id"], ["work_centers.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "routing_id", "seq_no", name="uq_routing_ops_tenant_routing_seq"),
        sa.Index("ix_routing_ops_tenant_routing", "tenant_id", "routing_id"),
    )

    # BOM and lines
    op.create_table(
        "boms",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("item_id", sa.UUID(), nullable=True),
        sa.Column("revision", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_boms_tenant_code"),
        sa.Index("ix_boms_tenant_code", "tenant_id", "code"),
    )

    op.create_table(
        "bom_lines",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("bom_id", sa.UUID(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("component_item_id", sa.UUID(), nullable=False),
        sa.Column("qty_per", sa.Numeric(18, 6), nullable=False),
        sa.Column("uom_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bom_id"], ["boms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["component_item_id"], ["items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["uom_id"], ["units_of_measure.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "bom_id", "line_no", name="uq_bom_lines_tenant_bom_line"),
        sa.Index("ix_bom_lines_tenant_bom", "tenant_id", "bom_id"),
    )

    # Enable RLS for new tables
    for tbl in [
        "units_of_measure",
        "items",
        "work_centers",
        "routings",
        "routing_operations",
        "boms",
        "bom_lines",
    ]:
        _enable_rls_with_policy(tbl)

    # Generic performance indexes: tenant_id, status, created_at, and common FKs
    # Use IF NOT EXISTS to avoid conflicts if some indexes already present.
    tenant_tables = [
        # Existing tenant-scoped tables
        "users", "roles", "permissions", "user_roles", "role_permissions",
        "org_units", "audit_log", "notifications",
        "locations", "lots", "inventory_transactions",
        "suppliers", "purchase_orders", "purchase_order_lines",
        "customers", "sales_orders", "sales_order_lines",
        "work_orders", "work_order_operations", "production_logs", "production_status_events",
        "inspections", "nonconformances",
        "assets", "maintenance_work_orders", "maintenance_logs",
        "events", "kpi_measurements",
        # New tables
        "units_of_measure", "items", "work_centers",
        "routings", "routing_operations", "boms", "bom_lines",
    ]
    for tbl in tenant_tables:
        op.execute(f'CREATE INDEX IF NOT EXISTS ix_{tbl}_tenant_id ON {tbl} (tenant_id);')

    status_tables = [
        "users", "purchase_orders", "sales_orders", "work_orders",
        "work_order_operations", "nonconformances", "assets",
        "maintenance_work_orders", "inspections", "items", "work_centers",
    ]
    for tbl in status_tables:
        # status column may not exist on all listed tables; guard via dynamic SQL
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='{tbl}' AND column_name='status') THEN
                    EXECUTE 'CREATE INDEX IF NOT EXISTS ix_{tbl}_tenant_status ON {tbl} (tenant_id, status)';
                END IF;
            END $$;
            """
        )

    created_at_tables = [
        # Most tenant tables have created_at; some already have composite indexes. This creates only if missing name.
        "users", "roles", "permissions", "user_roles", "role_permissions",
        "org_units", "locations", "lots", "inventory_transactions",
        "suppliers", "purchase_orders", "purchase_order_lines",
        "customers", "sales_orders", "sales_order_lines",
        "work_orders", "work_order_operations", "production_logs", "production_status_events",
        "inspections", "nonconformances",
        "assets", "maintenance_work_orders", "maintenance_logs",
        "events", "kpi_measurements",
        "units_of_measure", "items", "work_centers",
        "routings", "routing_operations", "boms", "bom_lines",
    ]
    for tbl in created_at_tables:
        op.execute(f'CREATE INDEX IF NOT EXISTS ix_{tbl}_tenant_created_at ON {tbl} (tenant_id, created_at);')

    # Common FK indexes (composite with tenant_id for RLS effectiveness)
    fk_indexes = {
        "purchase_orders": ["supplier_id"],
        "purchase_order_lines": ["purchase_order_id"],
        "sales_orders": ["customer_id"],
        "sales_order_lines": ["sales_order_id"],
        "work_orders": ["sales_order_id", "bom_id", "routing_id"],
        "work_order_operations": ["work_order_id"],
        "production_logs": ["work_order_id", "operation_id", "created_by"],
        "inspections": ["lot_id", "work_order_id", "inspector_id"],
        "maintenance_work_orders": ["asset_id", "created_by"],
        "maintenance_logs": ["maintenance_work_order_id"],
        "inventory_transactions": ["lot_id", "from_location_id", "to_location_id"],
        "assets": ["location_id"],
        "production_status_events": ["entity_id"],
        "routing_operations": ["routing_id", "work_center_id"],
        "routings": ["item_id"],
        "boms": ["item_id"],
        "bom_lines": ["bom_id", "component_item_id", "uom_id"],
        "items": ["default_uom_id"],
        "work_centers": ["asset_id"],
    }
    for tbl, cols in fk_indexes.items():
        for col in cols:
            op.execute(f'CREATE INDEX IF NOT EXISTS ix_{tbl}_tenant_fk_{col} ON {tbl} (tenant_id, {col});')


def downgrade() -> None:
    # Drop RLS policies and disable on new tables
    for tbl in [
        "bom_lines", "boms", "routing_operations", "routings", "work_centers", "items", "units_of_measure"
    ]:
        op.execute(f"DROP POLICY IF EXISTS {tbl}_tenant_isolation ON {tbl};")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY;")

    # Drop new tables in reverse dependency order
    op.drop_table("bom_lines")
    op.drop_table("boms")
    op.drop_table("routing_operations")
    op.drop_table("routings")
    op.drop_table("work_centers")
    op.drop_table("items")
    op.drop_table("units_of_measure")

    # Note: Generic indexes on existing tables are left in place for safety.
