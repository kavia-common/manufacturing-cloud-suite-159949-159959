from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.settings import get_app_settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# PUBLIC_INTERFACE
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password using bcrypt."""
    return _pwd_context.verify(plain_password, hashed_password)


# PUBLIC_INTERFACE
def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return _pwd_context.hash(password)


def _create_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta],
    token_type: str,
) -> str:
    settings = get_app_settings()
    to_encode = data.copy()
    now = datetime.now(tz=timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire, "iat": now, "type": token_type})
    encoded_jwt = jwt.encode(
        to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


# PUBLIC_INTERFACE
def create_access_token(
    subject: str,
    tenant_id: str,
    roles: list[str] | None = None,
    expires_minutes: Optional[int] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    """Create a signed access token with subject (user id), tenant claim and roles."""
    settings = get_app_settings()
    exp = timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: Dict[str, Any] = {"sub": subject, "tenant_id": tenant_id, "roles": roles or []}
    if extra:
        payload.update(extra)
    return _create_token(payload, exp, token_type="access")


# PUBLIC_INTERFACE
def create_refresh_token(
    subject: str, tenant_id: str, expires_minutes: Optional[int] = None
) -> str:
    """Create a signed refresh token with subject and tenant claim."""
    settings = get_app_settings()
    exp = timedelta(minutes=expires_minutes or settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "tenant_id": tenant_id}
    return _create_token(payload, exp, token_type="refresh")


# PUBLIC_INTERFACE
def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT; raises JWTError if invalid/expired."""
    settings = get_app_settings()
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# PUBLIC_INTERFACE
def get_token_subject(token: str) -> Optional[str]:
    """Return 'sub' from a token or None when token is invalid."""
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except JWTError:
        return None
