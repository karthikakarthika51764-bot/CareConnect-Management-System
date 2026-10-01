from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token, create_refresh_token, get_current_user, hash_password, token_digest, verify_password
from app.db import get_db
from app.models import Business, User
from app.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def issue_tokens(database: Session, user: User) -> TokenResponse:
    refresh_token = create_refresh_token(user)
    user.refresh_token_hash = token_digest(refresh_token)
    database.commit()
    return TokenResponse(access_token=create_access_token(user), refresh_token=refresh_token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, database: Session = Depends(get_db)):
    if database.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    business = Business(name=payload.business_name.strip())
    database.add(business)
    database.flush()
    user = User(
        business_id=business.id,
        name=payload.name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role="BUSINESS_OWNER",
    )
    database.add(user)
    try:
        database.commit()
    except IntegrityError:
        database.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists") from None
    database.refresh(user)
    return issue_tokens(database, user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, database: Session = Depends(get_db)):
    user = database.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email or password is incorrect")
    return issue_tokens(database, user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, database: Session = Depends(get_db)):
    import jwt
    from app.core.config import settings

    try:
        token_payload = jwt.decode(payload.refresh_token, settings.secret_key, algorithms=["HS256"])
        if token_payload.get("type") != "refresh":
            raise jwt.InvalidTokenError("Expected a refresh token")
        user_id = int(token_payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired") from None
    user = database.get(User, user_id)
    if user is None or user.refresh_token_hash != token_digest(payload.refresh_token):
        raise HTTPException(status_code=401, detail="Refresh token has already been used or revoked")
    return issue_tokens(database, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(user: User = Depends(get_current_user), database: Session = Depends(get_db)):
    user.refresh_token_hash = None
    database.commit()


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
