"""Extend domain schema for production, inventory, procurement, sales, quality, maintenance, and analytics.

Adds tenant-scoped tables with UUID PKs, timestamps, indexes, and RLS policies:
- Inventory: locations, lots, inventory_transactions
- Procurement: suppliers, purchase_orders, purchase_order_lines
- Sales: customers, sales_orders, sales_order_lines
- Production: work_orders, work_order_operations, production_logs, production_status_events
- Quality: inspections, nonconformances
- Maintenance: assets, maintenance_work_orders, maintenance_logs
- Analytics: events, kpi_measurements
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a2e4f7c1b8d2"
down_revision: Union[str, None] = "9f0b6b3a9a01"
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
    # INVENTORY
    op.create_table(
        "locations",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("parent_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["locations.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_locations_tenant_code"),
        sa.Index("ix_locations_tenant_code", "tenant_id", "code"),
    )

    op.create_table(
        "lots",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("lot_no", sa.Text(), nullable=False),
        sa.Column("item_sku", sa.Text(), nullable=False),
        sa.Column("uom", sa.Text(), nullable=True),
        sa.Column("quantity_on_hand", sa.Numeric(18, 6), nullable=True),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "lot_no", name="uq_lots_tenant_lot_no"),
        sa.Index("ix_lots_tenant_lot", "tenant_id", "lot_no"),
    )

    op.create_table(
        "inventory_transactions",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("lot_id", sa.UUID(), nullable=True),
        sa.Column("from_location_id", sa.UUID(), nullable=True),
        sa.Column("to_location_id", sa.UUID(), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("uom", sa.Text(), nullable=True),
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.Column("ref_type", sa.Text(), nullable=True),
        sa.Column("ref_id", sa.UUID(), nullable=True),
        sa.Column("metadata", sa.JSON(), server_default=JSONB_EMPTY, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["from_location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.Index("ix_inventory_txn_tenant_created_at", "tenant_id", "created_at"),
    )

    # PROCUREMENT
    op.create_table(
        "suppliers",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("address", sa.JSON(), server_default=JSONB_EMPTY, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_suppliers_tenant_code"),
        sa.Index("ix_suppliers_tenant_code", "tenant_id", "code"),
    )

    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("po_number", sa.Text(), nullable=False),
        sa.Column("supplier_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("order_date", sa.Date(), nullable=True),
        sa.Column("expected_date", sa.Date(), nullable=True),
        sa.Column("total_amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "po_number", name="uq_purchase_orders_tenant_po_number"),
        sa.Index("ix_purchase_orders_tenant_po", "tenant_id", "po_number"),
    )

    op.create_table(
        "purchase_order_lines",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("purchase_order_id", sa.UUID(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("item_sku", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("qty_ordered", sa.Numeric(18, 6), nullable=False),
        sa.Column("qty_received", sa.Numeric(18, 6), nullable=True),
        sa.Column("uom", sa.Text(), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["purchase_order_id"], ["purchase_orders.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "purchase_order_id", "line_no", name="uq_po_lines_tenant_po_line"),
    )

    # SALES
    op.create_table(
        "customers",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("billing_address", sa.JSON(), server_default=JSONB_EMPTY, nullable=False),
        sa.Column("shipping_address", sa.JSON(), server_default=JSONB_EMPTY, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_customers_tenant_code"),
        sa.Index("ix_customers_tenant_code", "tenant_id", "code"),
    )

    op.create_table(
        "sales_orders",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("so_number", sa.Text(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("order_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("total_amount", sa.Numeric(18, 6), nullable=True),
        sa.Column("currency", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("tenant_id", "so_number", name="uq_sales_orders_tenant_so_number"),
        sa.Index("ix_sales_orders_tenant_so", "tenant_id", "so_number"),
    )

    op.create_table(
        "sales_order_lines",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("sales_order_id", sa.UUID(), nullable=False),
        sa.Column("line_no", sa.Integer(), nullable=False),
        sa.Column("item_sku", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("qty_ordered", sa.Numeric(18, 6), nullable=False),
        sa.Column("qty_shipped", sa.Numeric(18, 6), nullable=True),
        sa.Column("uom", sa.Text(), nullable=True),
        sa.Column("unit_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "sales_order_id", "line_no", name="uq_so_lines_tenant_so_line"),
    )

    # PRODUCTION
    op.create_table(
        "work_orders",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("order_no", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("item_sku", sa.Text(), nullable=True),
        sa.Column("quantity_planned", sa.Numeric(18, 6), nullable=True),
        sa.Column("quantity_completed", sa.Numeric(18, 6), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("sales_order_id", sa.UUID(), nullable=True),
        sa.Column("bom_id", sa.UUID(), nullable=True),
        sa.Column("routing_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sales_order_id"], ["sales_orders.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "order_no", name="uq_work_orders_tenant_order_no"),
        sa.Index("ix_work_orders_tenant_order_no", "tenant_id", "order_no"),
    )

    op.create_table(
        "work_order_operations",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("work_order_id", sa.UUID(), nullable=False),
        sa.Column("seq_no", sa.Integer(), nullable=False),
        sa.Column("operation_code", sa.Text(), nullable=True),
        sa.Column("work_center", sa.Text(), nullable=True),
        sa.Column("planned_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("quantity_good", sa.Numeric(18, 6), nullable=True),
        sa.Column("quantity_scrap", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("tenant_id", "work_order_id", "seq_no", name="uq_wo_ops_tenant_wo_seq"),
    )

    op.create_table(
        "production_logs",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("work_order_id", sa.UUID(), nullable=True),
        sa.Column("operation_id", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("log_type", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=True),
        sa.Column("duration_minutes", sa.Numeric(18, 6), nullable=True),
        sa.Column("metadata", sa.JSON(), server_default=JSONB_EMPTY, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["operation_id"], ["work_order_operations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.Index("ix_production_logs_tenant_created_at", "tenant_id", "created_at"),
    )

    op.create_table(
        "production_status_events",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.Index("ix_prod_status_events_tenant_entity", "tenant_id", "entity_type", "entity_id"),
    )

    # QUALITY
    op.create_table(
        "inspections",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("lot_id", sa.UUID(), nullable=True),
        sa.Column("work_order_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("inspector_id", sa.UUID(), nullable=True),
        sa.Column("inspection_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data", sa.JSON(), server_default=JSONB_EMPTY, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lot_id"], ["lots.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["work_order_id"], ["work_orders.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inspector_id"], ["users.id"], ondelete="SET NULL"),
        sa.Index("ix_inspections_tenant_created_at", "tenant_id", "created_at"),
    )

    op.create_table(
        "nonconformances",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("source_type", sa.Text(), nullable=True),
        sa.Column("source_id", sa.UUID(), nullable=True),
        sa.Column("severity", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("disposition", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.Index("ix_nonconformances_tenant_status", "tenant_id", "status"),
    )

    # MAINTENANCE
    op.create_table(
        "assets",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=True),
        sa.Column("location_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_assets_tenant_code"),
        sa.Index("ix_assets_tenant_code", "tenant_id", "code"),
    )

    op.create_table(
        "maintenance_work_orders",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("asset_id", sa.UUID(), nullable=True),
        sa.Column("wo_number", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requested_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("tenant_id", "wo_number", name="uq_maint_wos_tenant_wo_number"),
        sa.Index("ix_maint_wos_tenant_wo", "tenant_id", "wo_number"),
    )

    op.create_table(
        "maintenance_logs",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("maintenance_work_order_id", sa.UUID(), nullable=False),
        sa.Column("log_type", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("duration_minutes", sa.Numeric(18, 6), nullable=True),
        sa.Column("cost", sa.Numeric(18, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["maintenance_work_order_id"], ["maintenance_work_orders.id"], ondelete="CASCADE"),
        sa.Index("ix_maint_logs_tenant_created_at", "tenant_id", "created_at"),
    )

    # ANALYTICS/EVENTS
    op.create_table(
        "events",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=True),
        sa.Column("entity_id", sa.UUID(), nullable=True),
        sa.Column("severity", sa.Text(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), server_default=JSONB_EMPTY, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.Index("ix_events_tenant_created_at", "tenant_id", "created_at"),
    )

    op.create_table(
        "kpi_measurements",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=UUID_DEFAULT),
        sa.Column("tenant_id", sa.UUID(), nullable=False, server_default=TENANT_DEFAULT),
        sa.Column("metric_name", sa.Text(), nullable=False),
        sa.Column("value", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit", sa.Text(), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dimensions", sa.JSON(), server_default=JSONB_EMPTY, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=NOW, nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.Index("ix_kpi_measurements_tenant_metric_at", "tenant_id", "metric_name", "at"),
    )

    # Enable RLS for tenant scoped tables
    tenant_scoped = [
        "locations",
        "lots",
        "inventory_transactions",
        "suppliers",
        "purchase_orders",
        "purchase_order_lines",
        "customers",
        "sales_orders",
        "sales_order_lines",
        "work_orders",
        "work_order_operations",
        "production_logs",
        "production_status_events",
        "inspections",
        "nonconformances",
        "assets",
        "maintenance_work_orders",
        "maintenance_logs",
        "events",
        "kpi_measurements",
    ]
    for tbl in tenant_scoped:
        _enable_rls_with_policy(tbl)


def downgrade() -> None:
    # Drop RLS policies and disable RLS
    tenant_scoped = [
        "kpi_measurements",
        "events",
        "maintenance_logs",
        "maintenance_work_orders",
        "assets",
        "nonconformances",
        "inspections",
        "production_status_events",
        "production_logs",
        "work_order_operations",
        "work_orders",
        "sales_order_lines",
        "sales_orders",
        "customers",
        "purchase_order_lines",
        "purchase_orders",
        "suppliers",
        "inventory_transactions",
        "lots",
        "locations",
    ]
    for tbl in tenant_scoped:
        op.execute(f"DROP POLICY IF EXISTS {tbl}_tenant_isolation ON {tbl};")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY;")

    # Drop tables in reverse dependency-safe order
    op.drop_table("kpi_measurements")
    op.drop_table("events")
    op.drop_table("maintenance_logs")
    op.drop_table("maintenance_work_orders")
    op.drop_table("assets")
    op.drop_table("nonconformances")
    op.drop_table("inspections")
    op.drop_table("production_status_events")
    op.drop_table("production_logs")
    op.drop_table("work_order_operations")
    op.drop_table("work_orders")
    op.drop_table("sales_order_lines")
    op.drop_table("sales_orders")
    op.drop_table("customers")
    op.drop_table("purchase_order_lines")
    op.drop_table("purchase_orders")
    op.drop_table("suppliers")
    op.drop_table("inventory_transactions")
    op.drop_table("lots")
    op.drop_table("locations")
