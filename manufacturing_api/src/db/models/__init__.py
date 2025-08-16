"""
ORM models for domain entities across production, inventory, procurement,
sales, quality, maintenance, and analytics.

Importing this package ensures model classes are registered with the Base
metadata for Alembic and runtime usage.
"""

# Re-export commonly used models for convenience and to ensure import side-effects
# register all mapped classes with SQLAlchemy metadata.

from .inventory import (  # noqa: F401
    Location,
    Lot,
    InventoryTransaction,
)
from .procurement import (  # noqa: F401
    Supplier,
    PurchaseOrder,
    PurchaseOrderLine,
)
from .sales import (  # noqa: F401
    Customer,
    SalesOrder,
    SalesOrderLine,
)
from .production import (  # noqa: F401
    WorkOrder,
    WorkOrderOperation,
    ProductionLog,
    ProductionStatusEvent,
)
from .quality import (  # noqa: F401
    Inspection,
    Nonconformance,
)
from .maintenance import (  # noqa: F401
    Asset,
    MaintenanceWorkOrder,
    MaintenanceLog,
)
from .analytics import (  # noqa: F401
    Event,
    KpiMeasurement,
)
