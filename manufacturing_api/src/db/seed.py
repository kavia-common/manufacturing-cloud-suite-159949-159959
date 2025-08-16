"""
Database seeding utilities for minimal reference data.

Seeds:
- Base tenant (Acme Manufacturing)
- Admin role and base permissions
- Example units of measure (EA, KG, HR)
- Sample items (RAW-AL-ROD, WIDGET-100)
- Work center (machine) with linked asset
- Routing and BOM for sample product

Usage:
  python -m src.db.run_migrations upgrade head
  python -m src.db.seed
"""

from __future__ import annotations

import asyncio
from typing import List, Tuple
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_async_session, tenant_context


# PUBLIC_INTERFACE
async def seed_all() -> None:
    """
    Seed the database with minimal reference data.

    This function:
      - Creates or retrieves a base tenant
      - Seeds admin role and base permissions
      - Seeds UoMs, items, a work center, and a simple routing/BOM
    """
    # Create a standalone session via dependency to reuse engine configuration.
    async for session in get_async_session():
        # Ensure base tenant exists (RLS-aware)
        tenant_id = await _ensure_base_tenant(session, name="Acme Manufacturing", slug="acme")
        async with tenant_context(session, tenant_id):
            await _seed_security(session)
            uoms = await _seed_uoms(session)
            items = await _seed_items(session, uoms)
            wc = await _seed_work_center(session)
            await _seed_routing_and_bom(session, items, uoms, wc)

        # Reset tenant context handled by tenant_context
        await session.commit()


async def _ensure_base_tenant(session: AsyncSession, name: str, slug: str) -> UUID:
    """
    Ensure a tenant row exists. RLS on tenants requires setting app.tenant_id
    to the same id being inserted (WITH CHECK id = current_setting()).
    """
    # Attempt to fetch existing
    res = await session.execute(text("SELECT id FROM tenants WHERE slug = :slug"), {"slug": slug})
    row = res.first()
    if row:
        return row[0]

    # Create deterministic new id and set GUC to insert through RLS
    tenant_id = uuid4()
    # Set GUC for this connection; reuse session for both set and insert
    await session.execute(text("SELECT set_config('app.tenant_id', :tid, false)"), {"tid": str(tenant_id)})
    await session.execute(
        text("INSERT INTO tenants (id, name, slug) VALUES (:id, :name, :slug) ON CONFLICT (slug) DO NOTHING"),
        {"id": str(tenant_id), "name": name, "slug": slug},
    )
    # Fetch id in case it raced
    res = await session.execute(text("SELECT id FROM tenants WHERE slug = :slug"), {"slug": slug})
    row = res.first()
    if not row:
        raise RuntimeError("Failed to create or load base tenant")
    return row[0]


async def _seed_security(session: AsyncSession) -> None:
    """
    Seed a minimal admin role and base permissions, and tie them together.
    """
    # Define a base set of permissions
    perm_codes = [
        "admin:all",
        "users:manage",
        "roles:manage",
        "inventory:view",
        "inventory:manage",
        "production:view",
        "production:manage",
        "quality:view",
        "quality:manage",
        "procurement:view",
        "procurement:manage",
        "sales:view",
        "sales:manage",
        "maintenance:view",
        "maintenance:manage",
        "analytics:view",
    ]

    # Insert permissions (tenant-scoped) - ignore if exist
    for code in perm_codes:
        await session.execute(
            text(
                """
                INSERT INTO permissions (tenant_id, code, description)
                VALUES (current_setting('app.tenant_id', true)::uuid, :code, :desc)
                ON CONFLICT ON CONSTRAINT uq_permissions_tenant_code DO NOTHING
                """
            ),
            {"code": code, "desc": code.replace(":", " ").title()},
        )

    # Upsert admin role
    await session.execute(
        text(
            """
            INSERT INTO roles (tenant_id, name, description)
            VALUES (current_setting('app.tenant_id', true)::uuid, 'admin', 'Administrator')
            ON CONFLICT ON CONSTRAINT uq_roles_tenant_name DO NOTHING
            """
        )
    )

    # Map all permissions to admin role
    res = await session.execute(
        text("SELECT id FROM roles WHERE name = 'admin' AND tenant_id = current_setting('app.tenant_id', true)::uuid")
    )
    role_row = res.first()
    if not role_row:
        return
    role_id = role_row[0]

    perm_ids = await session.execute(
        text("SELECT id FROM permissions WHERE tenant_id = current_setting('app.tenant_id', true)::uuid")
    )
    for (pid,) in perm_ids.all():
        await session.execute(
            text(
                """
                INSERT INTO role_permissions (tenant_id, role_id, permission_id)
                VALUES (current_setting('app.tenant_id', true)::uuid, :rid, :pid)
                ON CONFLICT ON CONSTRAINT uq_role_permissions_tenant_role_permission DO NOTHING
                """
            ),
            {"rid": str(role_id), "pid": str(pid)},
        )


async def _seed_uoms(session: AsyncSession) -> dict[str, UUID]:
    """
    Seed example units of measure and return a mapping code->id.

    Returns:
      dict mapping UoM code to id
    """
    uoms: List[Tuple[str, str, str | None]] = [
        ("EA", "Each", "quantity"),
        ("KG", "Kilogram", "mass"),
        ("HR", "Hour", "time"),
    ]
    ids: dict[str, UUID] = {}

    for code, desc, cat in uoms:
        # Try to get existing id
        res = await session.execute(
            text(
                """
                SELECT id FROM units_of_measure
                WHERE tenant_id = current_setting('app.tenant_id', true)::uuid AND code = :code
                """
            ),
            {"code": code},
        )
        row = res.first()
        if row:
            ids[code] = row[0]
            continue

        # Insert new
        inserted = await session.execute(
            text(
                """
                INSERT INTO units_of_measure (tenant_id, code, description, category)
                VALUES (current_setting('app.tenant_id', true)::uuid, :code, :desc, :cat)
                RETURNING id
                """
            ),
            {"code": code, "desc": desc, "cat": cat},
        )
        ids[code] = inserted.scalar_one()
    return ids


async def _seed_items(session: AsyncSession, uoms: dict[str, UUID]) -> dict[str, UUID]:
    """
    Seed a raw material and a finished good item.

    Returns:
      dict mapping SKU->id
    """
    items = [
        ("RAW-AL-ROD", "Aluminum Rod Raw", "Raw material", uoms.get("KG")),
        ("WIDGET-100", "Sample Widget", "Finished good", uoms.get("EA")),
    ]
    result: dict[str, UUID] = {}

    for sku, name, desc, uom_id in items:
        res = await session.execute(
            text(
                """
                SELECT id FROM items
                WHERE tenant_id = current_setting('app.tenant_id', true)::uuid AND sku = :sku
                """
            ),
            {"sku": sku},
        )
        row = res.first()
        if row:
            result[sku] = row[0]
            continue

        inserted = await session.execute(
            text(
                """
                INSERT INTO items (tenant_id, sku, name, description, default_uom_id, status)
                VALUES (current_setting('app.tenant_id', true)::uuid, :sku, :name, :desc, :uom_id, 'active')
                RETURNING id
                """
            ),
            {"sku": sku, "name": name, "desc": desc, "uom_id": str(uom_id) if uom_id else None},
        )
        result[sku] = inserted.scalar_one()

    return result


async def _seed_work_center(session: AsyncSession) -> UUID:
    """
    Seed a single work center and a corresponding asset if needed.

    Returns:
      work_center_id
    """
    # Ensure an Asset exists to tie (optional)
    # Create asset if missing
    res = await session.execute(
        text(
            """
            SELECT id FROM assets
            WHERE tenant_id = current_setting('app.tenant_id', true)::uuid AND code = 'CNC-01'
            """
        )
    )
    asset_row = res.first()
    if not asset_row:
        inserted = await session.execute(
            text(
                """
                INSERT INTO assets (tenant_id, code, name, type, status)
                VALUES (current_setting('app.tenant_id', true)::uuid, 'CNC-01', 'CNC Mill 01', 'machine', 'active')
                RETURNING id
                """
            )
        )
        asset_id = inserted.scalar_one()
    else:
        asset_id = asset_row[0]

    # Create or get work center
    res = await session.execute(
        text(
            """
            SELECT id FROM work_centers
            WHERE tenant_id = current_setting('app.tenant_id', true)::uuid AND code = 'WC-100'
            """
        )
    )
    row = res.first()
    if row:
        return row[0]

    inserted = await session.execute(
        text(
            """
            INSERT INTO work_centers (tenant_id, code, name, type, status, asset_id)
            VALUES (current_setting('app.tenant_id', true)::uuid, 'WC-100', 'CNC Milling Center', 'machine', 'available', :asset_id)
            RETURNING id
            """
        ),
        {"asset_id": str(asset_id)},
    )
    return inserted.scalar_one()


async def _seed_routing_and_bom(
    session: AsyncSession,
    items: dict[str, UUID],
    uoms: dict[str, UUID],
    work_center_id: UUID,
) -> None:
    """
    Create a single-operation routing and a single-line BOM for the sample item.
    """
    fg_id = items["WIDGET-100"]
    rm_id = items["RAW-AL-ROD"]

    # Routing
    res = await session.execute(
        text(
            """
            SELECT id FROM routings
            WHERE tenant_id = current_setting('app.tenant_id', true)::uuid AND code = 'RT-WIDGET-100'
            """
        )
    )
    row = res.first()
    if row:
        routing_id = row[0]
    else:
        inserted = await session.execute(
            text(
                """
                INSERT INTO routings (tenant_id, code, item_id, revision, is_active)
                VALUES (current_setting('app.tenant_id', true)::uuid, 'RT-WIDGET-100', :item_id, 'A', true)
                RETURNING id
                """
            ),
            {"item_id": str(fg_id)},
        )
        routing_id = inserted.scalar_one()

    # Routing operation (single step)
    await session.execute(
        text(
            """
            INSERT INTO routing_operations (tenant_id, routing_id, seq_no, operation_code, work_center_id, standard_time_minutes)
            VALUES (current_setting('app.tenant_id', true)::uuid, :rid, 10, 'MILLING', :wc, 30)
            ON CONFLICT ON CONSTRAINT uq_routing_ops_tenant_routing_seq DO NOTHING
            """
        ),
        {"rid": str(routing_id), "wc": str(work_center_id)},
    )

    # BOM
    res = await session.execute(
        text(
            """
            SELECT id FROM boms
            WHERE tenant_id = current_setting('app.tenant_id', true)::uuid AND code = 'BOM-WIDGET-100'
            """
        )
    )
    row = res.first()
    if row:
        bom_id = row[0]
    else:
        inserted = await session.execute(
            text(
                """
                INSERT INTO boms (tenant_id, code, item_id, revision, is_active)
                VALUES (current_setting('app.tenant_id', true)::uuid, 'BOM-WIDGET-100', :item_id, 'A', true)
                RETURNING id
                """
            ),
            {"item_id": str(fg_id)},
        )
        bom_id = inserted.scalar_one()

    # BOM line for raw material
    await session.execute(
        text(
            """
            INSERT INTO bom_lines (tenant_id, bom_id, line_no, component_item_id, qty_per, uom_id)
            VALUES (current_setting('app.tenant_id', true)::uuid, :bid, 1, :rm, 1.50, :uom)
            ON CONFLICT ON CONSTRAINT uq_bom_lines_tenant_bom_line DO NOTHING
            """
        ),
        {"bid": str(bom_id), "rm": str(rm_id), "uom": str(uoms["KG"])},
    )


# PUBLIC_INTERFACE
def main() -> None:
    """Entrypoint to run the asynchronous seeding."""
    asyncio.run(seed_all())


if __name__ == "__main__":
    main()
