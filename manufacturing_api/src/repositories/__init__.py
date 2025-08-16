"""
Repository layer for data access.

Repositories encapsulate SQLAlchemy queries and patterns for each domain area.
They assume the provided AsyncSession has appropriate tenant context configured
(e.g., using src.core.deps.get_tenant_session dependency).
"""
