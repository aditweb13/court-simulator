"""FastAPI route dependencies."""

import uuid
from typing import Optional

from fastapi import Depends, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
