"""
Public Pydantic schemas used by FastAPI routes, services, and tests.

Schemas are grouped by domain module (inventory, production, etc.) and also
include common reusable models such as pagination and standard responses.
"""

from .common import MessageResponse  # noqa: F401
