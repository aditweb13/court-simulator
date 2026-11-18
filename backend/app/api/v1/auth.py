"""Authentication REST routes."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppException, ErrorCode, get_request_id
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.schemas.envelope import Meta, SuccessResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=SuccessResponse[AuthResponse],
    status_code=status.HTTP_201_CREATED,
)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[AuthResponse]:
    req_id = get_request_id(request)

    # Check for existing email
    stmt = select(User).where(User.email == body.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    if existing_user is not None:
        raise AppException(
            code=ErrorCode.CONFLICT,
            message="An account with this email already exists",
            status_code=status.HTTP_409_CONFLICT,
        )

    # Create new user
    user = User(
        email=body.email,
        password_hash=hash_password(body.password),
        display_name=body.display_name,
        is_guest=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(subject=user.id, is_guest=False)
    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_guest=user.is_guest,
        created_at=user.created_at,
    )

    return SuccessResponse(
        data=AuthResponse(access_token=token, token_type="bearer", user=user_resp),
        meta=Meta(request_id=req_id),
    )


@router.post(
    "/login",
    response_model=SuccessResponse[AuthResponse],
)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SuccessResponse[AuthResponse]:
    req_id = get_request_id(request)

    stmt = select(User).where(User.email == body.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if (
        user is None
        or not user.password_hash
        or not verify_password(body.password, user.password_hash)
    ):
        raise AppException(
            code=ErrorCode.UNAUTHENTICATED,
            message="Invalid email or password",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = create_access_token(subject=user.id, is_guest=user.is_guest)
    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_guest=user.is_guest,
        created_at=user.created_at,
    )

    return SuccessResponse(
        data=AuthResponse(access_token=token, token_type="bearer", user=user_resp),
        meta=Meta(request_id=req_id),
    )
