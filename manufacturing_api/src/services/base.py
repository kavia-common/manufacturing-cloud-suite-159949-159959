from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


class BaseService:
    """
    Base class for services. Holds a session for use across multiple repositories.

    Services should keep business logic and orchestration, delegating data access
    to repositories.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
