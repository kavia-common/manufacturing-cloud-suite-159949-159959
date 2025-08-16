from __future__ import annotations

import io
from datetime import date, datetime
from typing import Optional, Sequence

import pandas as pd
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import Select, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.deps import get_tenant_session, require_roles
from src.db.models.inventory import Lot

from src.db.models.procurement import PurchaseOrder, PurchaseOrderLine
from src.db.models.production import WorkOrder, WorkOrderOperation
from src.db.models.quality import Nonconformance

# PUBLIC_INTERFACE
router = APIRouter(
    prefix="/api/v1/reports",
    tags=["Reports"],
)


def _export_dataframe(
    df: pd.DataFrame,
    filename_base: str,
    export_format: str,
) -> StreamingResponse:
    """
    Convert DataFrame to the requested format and return a StreamingResponse.

    Supported formats:
      - csv: text/csv
      - xlsx: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
      - pdf: application/pdf (simple tabular rendering)
    """
    export_format = (export_format or "csv").lower()
    if export_format == "csv":
        buffer = io.StringIO()
        df.to_csv(buffer, index=False)
        buffer.seek(0)
        headers = {
            "Content-Disposition": f'attachment; filename="{filename_base}.csv"'
        }
        return StreamingResponse(
            buffer, media_type="text/csv", headers=headers
        )

    if export_format in ("xlsx", "excel", "xls", "xlsx"):
        # Use openpyxl engine
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Report")
        buffer.seek(0)
        headers = {
            "Content-Disposition": f'attachment; filename="{filename_base}.xlsx"'
        }
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers=headers,
        )

    if export_format == "pdf":
        # Render a very simple table using reportlab
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), leftMargin=18, rightMargin=18, topMargin=18, bottomMargin=18)
        elements: list = []
        styles = getSampleStyleSheet()
        title = Paragraph(f"{filename_base.replace('_', ' ').title()} ({datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')})", styles["Title"])
        elements.append(title)

        # Prepare data for table
        data = [list(df.columns)] + df.astype(str).values.tolist()
        table = Table(data, repeatRows=1)
        table_style = TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ]
        )
        table.setStyle(table_style)
        elements.append(table)
        doc.build(elements)
        buffer.seek(0)
        headers = {
            "Content-Disposition": f'attachment; filename="{filename_base}.pdf"'
        }
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)

    # Default: CSV
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    headers = {
        "Content-Disposition": f'attachment; filename="{filename_base}.csv"'
    }
    return StreamingResponse(buffer, media_type="text/csv", headers=headers)


async def _fetch_all(session: AsyncSession, stmt: Select) -> Sequence:
    """Execute a select and return list of ORM rows or row tuples."""
    res = await session.execute(stmt)
    return list(res.all())


# PUBLIC_INTERFACE
@router.get(
    "/inventory-valuation",
    summary="Inventory valuation report",
    description="Exports inventory valuation based on lots and last known PO line unit price per item SKU.",
    response_description="File stream (CSV/XLSX/PDF)",
    dependencies=[Depends(require_roles("admin", "reports:view", "inventory:view"))],
)
async def inventory_valuation_report(
    session: AsyncSession = Depends(get_tenant_session),
    as_of: Optional[date] = Query(None, description="As-of date for valuation (currently informational)"),
    format: str = Query("csv", description="Export format: csv | xlsx | pdf"),
):
    """
    Generate an Inventory Valuation report.

    This report lists lots with quantity on hand and estimates value using the latest
    purchase order line unit_price for the same item_sku (if available).
    """
    # Latest unit price per item (scalar subquery)
    sub_last_price = (
        select(PurchaseOrderLine.unit_price)
        .where(PurchaseOrderLine.item_sku == Lot.item_sku)
        .order_by(PurchaseOrderLine.created_at.desc())
        .limit(1)
        .scalar_subquery()
    )

    stmt = (
        select(
            Lot.item_sku,
            Lot.lot_no,
            Lot.uom,
            Lot.quantity_on_hand,
            Lot.status,
            Lot.created_at,
            Lot.updated_at,
            sub_last_price.label("unit_price"),
        )
        .order_by(Lot.item_sku, Lot.lot_no)
    )

    rows = await _fetch_all(session, stmt)
    # rows are tuples in the order of selected columns
    data = []
    for (
        item_sku,
        lot_no,
        uom,
        qty_on_hand,
        status,
        created_at,
        updated_at,
        unit_price,
    ) in rows:
        qty = float(qty_on_hand or 0)
        price = float(unit_price or 0)
        value = qty * price
        data.append(
            {
                "item_sku": item_sku,
                "lot_no": lot_no,
                "uom": uom,
                "quantity_on_hand": qty,
                "unit_price": price if unit_price is not None else None,
                "valuation": value if unit_price is not None else None,
                "status": status,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )

    df = pd.DataFrame(data, columns=[
        "item_sku",
        "lot_no",
        "uom",
        "quantity_on_hand",
        "unit_price",
        "valuation",
        "status",
        "created_at",
        "updated_at",
    ])
    return _export_dataframe(df, "inventory_valuation", format)


# PUBLIC_INTERFACE
@router.get(
    "/work-order-status",
    summary="Work order status report",
    description="Exports work orders with operation counts and completion progress.",
    response_description="File stream (CSV/XLSX/PDF)",
    dependencies=[Depends(require_roles("admin", "reports:view", "production:view"))],
)
async def work_order_status_report(
    session: AsyncSession = Depends(get_tenant_session),
    status: Optional[str] = Query(None, description="Filter by work order status"),
    format: str = Query("csv", description="Export format: csv | xlsx | pdf"),
):
    """
    Generate a Work Order Status report.

    Includes:
      - work order header fields
      - total and completed operations (by status = 'completed')
      - completion percentage based on quantity_completed/quantity_planned when available
    """
    total_ops_sub = (
        select(func.count(WorkOrderOperation.id))
        .where(WorkOrderOperation.work_order_id == WorkOrder.id)
        .scalar_subquery()
    )
    completed_ops_sub = (
        select(func.count(WorkOrderOperation.id))
        .where(
            (WorkOrderOperation.work_order_id == WorkOrder.id)
            & (WorkOrderOperation.status == "completed")
        )
        .scalar_subquery()
    )

    stmt = select(
        WorkOrder.order_no,
        WorkOrder.status,
        WorkOrder.item_sku,
        WorkOrder.quantity_planned,
        WorkOrder.quantity_completed,
        WorkOrder.due_date,
        WorkOrder.start_date,
        WorkOrder.end_date,
        WorkOrder.priority,
        WorkOrder.created_at,
        WorkOrder.updated_at,
        total_ops_sub.label("total_ops"),
        completed_ops_sub.label("completed_ops"),
    ).order_by(WorkOrder.created_at.desc())

    if status:
        stmt = stmt.where(WorkOrder.status == status)

    rows = await _fetch_all(session, stmt)
    data = []
    for (
        order_no,
        wo_status,
        item_sku,
        qty_planned,
        qty_completed,
        due_date,
        start_date,
        end_date,
        priority,
        created_at,
        updated_at,
        total_ops,
        completed_ops,
    ) in rows:
        qp = float(qty_planned or 0)
        qc = float(qty_completed or 0)
        progress = (qc / qp * 100.0) if qp > 0 else None
        data.append(
            {
                "order_no": order_no,
                "status": wo_status,
                "item_sku": item_sku,
                "quantity_planned": qp if qty_planned is not None else None,
                "quantity_completed": qc if qty_completed is not None else None,
                "progress_percent": round(progress, 2) if progress is not None else None,
                "due_date": due_date,
                "start_date": start_date,
                "end_date": end_date,
                "priority": priority,
                "total_operations": int(total_ops or 0),
                "completed_operations": int(completed_ops or 0),
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
    df = pd.DataFrame(data, columns=[
        "order_no",
        "status",
        "item_sku",
        "quantity_planned",
        "quantity_completed",
        "progress_percent",
        "due_date",
        "start_date",
        "end_date",
        "priority",
        "total_operations",
        "completed_operations",
        "created_at",
        "updated_at",
    ])
    return _export_dataframe(df, "work_order_status", format)


# PUBLIC_INTERFACE
@router.get(
    "/supplier-delivery",
    summary="Supplier delivery report",
    description="Exports PO lines with received status, delivery risk heuristics, and past due flags.",
    response_description="File stream (CSV/XLSX/PDF)",
    dependencies=[Depends(require_roles("admin", "reports:view", "procurement:view"))],
)
async def supplier_delivery_report(
    session: AsyncSession = Depends(get_tenant_session),
    supplier_id: Optional[str] = Query(None, description="Filter by supplier UUID"),
    status: Optional[str] = Query(None, description="Filter POs by status"),
    format: str = Query("csv", description="Export format: csv | xlsx | pdf"),
):
    """
    Generate a Supplier Delivery report.

    Heuristics:
      - is_fully_received: qty_received >= qty_ordered
      - is_past_due: expected_date < today and not fully received
      - receive_rate_percent: (qty_received / qty_ordered * 100) when qty_ordered > 0
    """
    stmt = (
        select(
            PurchaseOrder.po_number,
            PurchaseOrder.supplier_id,
            PurchaseOrder.status,
            PurchaseOrder.order_date,
            PurchaseOrder.expected_date,
            PurchaseOrder.currency,
            PurchaseOrderLine.line_no,
            PurchaseOrderLine.item_sku,
            PurchaseOrderLine.description,
            PurchaseOrderLine.qty_ordered,
            PurchaseOrderLine.qty_received,
            PurchaseOrderLine.uom,
            PurchaseOrderLine.unit_price,
        )
        .join(PurchaseOrderLine, PurchaseOrderLine.purchase_order_id == PurchaseOrder.id)
        .order_by(PurchaseOrder.order_date.desc().nullslast(), PurchaseOrder.po_number, PurchaseOrderLine.line_no)
    )
    if supplier_id:
        # supplier_id provided as UUID string; rely on DB to validate via casting or string match
        stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)  # type: ignore[arg-type]
    if status:
        stmt = stmt.where(PurchaseOrder.status == status)

    rows = await _fetch_all(session, stmt)
    today = date.today()
    data = []
    for (
        po_number,
        sup_id,
        po_status,
        order_date,
        expected_date,
        currency,
        line_no,
        item_sku,
        description,
        qty_ordered,
        qty_received,
        uom,
        unit_price,
    ) in rows:
        qo = float(qty_ordered or 0)
        qr = float(qty_received or 0)
        fully_received = qr >= qo and qo > 0
        past_due = (expected_date is not None and expected_date < today) and not fully_received
        rate = (qr / qo * 100.0) if qo > 0 else None
        data.append(
            {
                "po_number": po_number,
                "supplier_id": str(sup_id) if sup_id else None,
                "status": po_status,
                "order_date": order_date,
                "expected_date": expected_date,
                "line_no": int(line_no),
                "item_sku": item_sku,
                "description": description,
                "qty_ordered": qo if qty_ordered is not None else None,
                "qty_received": qr if qty_received is not None else None,
                "uom": uom,
                "unit_price": float(unit_price) if unit_price is not None else None,
                "receive_rate_percent": round(rate, 2) if rate is not None else None,
                "is_fully_received": fully_received,
                "is_past_due": past_due,
                "currency": currency,
            }
        )

    df = pd.DataFrame(
        data,
        columns=[
            "po_number",
            "supplier_id",
            "status",
            "order_date",
            "expected_date",
            "line_no",
            "item_sku",
            "description",
            "qty_ordered",
            "qty_received",
            "uom",
            "unit_price",
            "receive_rate_percent",
            "is_fully_received",
            "is_past_due",
            "currency",
        ],
    )
    return _export_dataframe(df, "supplier_delivery", format)


# PUBLIC_INTERFACE
@router.get(
    "/quality-defects",
    summary="Quality defects report",
    description="Exports nonconformances with key attributes and status.",
    response_description="File stream (CSV/XLSX/PDF)",
    dependencies=[Depends(require_roles("admin", "reports:view", "quality:view"))],
)
async def quality_defects_report(
    session: AsyncSession = Depends(get_tenant_session),
    status: Optional[str] = Query(None, description="Filter nonconformances by status"),
    severity: Optional[str] = Query(None, description="Filter nonconformances by severity"),
    format: str = Query("csv", description="Export format: csv | xlsx | pdf"),
):
    """
    Generate a Quality Defects report (Nonconformances).
    """
    stmt = select(
        Nonconformance.id,
        Nonconformance.source_type,
        Nonconformance.source_id,
        Nonconformance.severity,
        Nonconformance.description,
        Nonconformance.disposition,
        Nonconformance.status,
        Nonconformance.closed_at,
        Nonconformance.created_at,
        Nonconformance.updated_at,
    ).order_by(Nonconformance.created_at.desc())

    if status:
        stmt = stmt.where(Nonconformance.status == status)
    if severity:
        stmt = stmt.where(Nonconformance.severity == severity)

    rows = await _fetch_all(session, stmt)
    data = []
    for (
        nc_id,
        source_type,
        source_id,
        sev,
        desc,
        disposition,
        st,
        closed_at,
        created_at,
        updated_at,
    ) in rows:
        data.append(
            {
                "id": str(nc_id),
                "source_type": source_type,
                "source_id": str(source_id) if source_id else None,
                "severity": sev,
                "description": desc,
                "disposition": disposition,
                "status": st,
                "closed_at": closed_at,
                "created_at": created_at,
                "updated_at": updated_at,
            }
        )
    df = pd.DataFrame(
        data,
        columns=[
            "id",
            "source_type",
            "source_id",
            "severity",
            "description",
            "disposition",
            "status",
            "closed_at",
            "created_at",
            "updated_at",
        ],
    )
    return _export_dataframe(df, "quality_defects", format)
