from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import create_access_token
from app.schemas.auth import Token, UserCreate, UserLogin, UserResponse
from app.services.user_store import user_store
from app.db.dependencies import get_db

router = APIRouter(prefix="/auth", tags=["Authentication & SRE Access"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new SRE user"
)
async def register(user_in: UserCreate, db: Session = Depends(get_db)) -> UserResponse:
    """
    Registers a new user with Argon2 password hashing.
    Enforces password complexity and uniqueness of username and email.
    """
    try:
        user = user_store.create_user(user_in, db=db)
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/login",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Log in and retrieve JWT bearer token"
)
async def login(credentials: UserLogin, db: Session = Depends(get_db)) -> Token:
    """
    Validates user credentials via Argon2 and issues a cryptographically signed JWT.
    Supports login via username or email.
    """
    user = user_store.authenticate_user(
        username_or_email=credentials.username_or_email,
        password=credentials.password,
        db=db,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=user.id,
        claims={"username": user.username, "role": user.role}
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user
    )


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user profile and permissions"
)
async def get_me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    """
    Returns the currently authenticated user's metadata and cluster access permissions.
    """
    return current_user
