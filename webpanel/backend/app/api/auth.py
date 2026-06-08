from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit.events import record_audit_event
from app.core.auth.dependencies import get_current_user
from app.core.auth.rate_limit import clear_login_attempts, is_login_limited, record_failed_login
from app.core.auth.security import (
    create_access_token,
    get_access_token_expire_minutes,
    hash_password,
    validate_password_policy,
    verify_password,
)
from app.core.notifications.events import create_notification
from app.core.rbac.permissions import get_user_permission_slugs, get_user_role_slugs
from app.db.models import User
from app.db.session import get_db


router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class MessageResponse(BaseModel):
    message: str


class CurrentUserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    is_active: bool
    is_superuser: bool


class CurrentAccessResponse(BaseModel):
    roles: list[str]
    permissions: list[str]


def _login_key(request: Request, email: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{email.lower()}"


@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    key = _login_key(request, payload.email)
    if is_login_limited(key):
        record_audit_event(
            db,
            action="auth.login.rate_limited",
            target_type="user",
            target_id=payload.email,
            outcome="failure",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many attempts")

    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash) or not user.is_active:
        record_failed_login(key)
        target_user_id = user.id if user is not None else None
        record_audit_event(
            db,
            action="auth.login.failed",
            target_type="user",
            target_id=payload.email,
            outcome="failure",
        )
        create_notification(
            db,
            title="Failed login",
            message=f"Failed login attempt for {payload.email}.",
            severity="warning",
            user_id=target_user_id,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    clear_login_attempts(key)
    record_audit_event(
        db,
        action="auth.login.succeeded",
        target_type="user",
        target_id=str(user.id),
        actor_user_id=user.id,
        outcome="success",
    )
    db.commit()

    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in_minutes=get_access_token_expire_minutes(),
    )


@router.post("/auth/password", response_model=MessageResponse)
def change_password(
    payload: PasswordChangeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    if not verify_password(payload.current_password, user.password_hash):
        record_audit_event(
            db,
            action="auth.password_change.failed",
            target_type="user",
            target_id=str(user.id),
            actor_user_id=user.id,
            outcome="failure",
            metadata={"reason": "invalid_current_password"},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid current password")

    policy_errors = validate_password_policy(payload.new_password)
    if policy_errors:
        record_audit_event(
            db,
            action="auth.password_change.failed",
            target_type="user",
            target_id=str(user.id),
            actor_user_id=user.id,
            outcome="failure",
            metadata={"reason": "password_policy"},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=policy_errors)

    user.password_hash = hash_password(payload.new_password)
    record_audit_event(
        db,
        action="auth.password_change.succeeded",
        target_type="user",
        target_id=str(user.id),
        actor_user_id=user.id,
        outcome="success",
    )
    db.commit()
    return MessageResponse(message="Password changed.")


@router.post("/auth/logout", response_model=MessageResponse)
def logout(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    record_audit_event(
        db,
        action="auth.logout.requested",
        target_type="user",
        target_id=str(user.id),
        actor_user_id=user.id,
        outcome="success",
        metadata={"mode": "stateless_bearer_token"},
    )
    db.commit()
    return MessageResponse(
        message="Logout is client-side for stateless bearer tokens; discard the token client-side."
    )


@router.get("/auth/me", response_model=CurrentUserResponse)
def current_user(user: User = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
    )


@router.get("/auth/permissions", response_model=CurrentAccessResponse)
def current_access(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CurrentAccessResponse:
    return CurrentAccessResponse(
        roles=sorted(get_user_role_slugs(db, user)),
        permissions=sorted(get_user_permission_slugs(db, user)),
    )
