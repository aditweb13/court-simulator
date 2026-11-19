"""FastAPI route dependencies."""

import uuid
from typing import Optional

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import AppException, ErrorCode
from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.session import get_db

http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate Bearer token, then load current user."""
    if credentials is None:
        raise AppException(
            code=ErrorCode.UNAUTHENTICATED,
            message="Authentication credentials required",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise ValueError("Token missing subject")
        user_id = uuid.UUID(user_id_str)
    except Exception:
        raise AppException(
            code=ErrorCode.UNAUTHENTICATED,
            message="Invalid or expired authentication token",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise AppException(
            code=ErrorCode.UNAUTHENTICATED,
            message="User session not found",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    return user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract and validate Bearer token if present, returning None if unauthenticated."""
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = uuid.UUID(user_id_str)
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    except Exception:
        return None


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Enforce that current_user has an email configured in ADMIN_EMAILS."""
    if (
        not current_user.email
        or current_user.email.strip().lower() not in settings.admin_emails_list
    ):
        raise AppException(
            code=ErrorCode.FORBIDDEN,
            message="Admin privileges required",
            status_code=status.HTTP_403_FORBIDDEN,
        )
    return current_user


admin_required = get_current_admin_user
