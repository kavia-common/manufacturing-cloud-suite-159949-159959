from __future__ import annotations

from typing import Any, Iterable, Optional

from sqlalchemy import Executable
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """
    Base class for repositories providing common helpers.

    Note:
      RLS enforcement is handled by Postgres using the `app.tenant_id` GUC.
      Ensure the session you're using has tenant context set via tenant_context.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def execute(self, statement: Executable, params: Optional[dict[str, Any]] = None):
        """Execute a SQLAlchemy statement."""
        return await self.session.execute(statement, params or {})

    async def scalars(self, statement: Executable, params: Optional[dict[str, Any]] = None):
        """Execute and return scalars."""
        result = await self.execute(statement, params)
        return result.scalars()

    async def scalar_one_or_none(self, statement: Executable, params: Optional[dict[str, Any]] = None):
        """Execute and return a single scalar or None."""
        result = await self.execute(statement, params)
        return result.scalar_one_or_none()

    async def commit(self) -> None:
        """Commit current transaction."""
        await self.session.commit()

    async def add_all(self, entities: Iterable[Any]) -> None:
        """Add multiple entities to session."""
        self.session.add_all(list(entities))

    async def add(self, entity: Any) -> None:
        """Add a single entity to session."""
        self.session.add(entity)
