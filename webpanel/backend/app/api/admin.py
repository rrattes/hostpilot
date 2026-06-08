from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.audit.events import record_audit_event
from app.core.auth.security import hash_password, validate_password_policy
from app.core.rbac.permissions import require_permission
from app.db.models import Role, User
from app.db.session import get_db


router = APIRouter()


class AdminStatus(BaseModel):
    status: str


class RoleUserRead(BaseModel):
    id: int
    email: str
    display_name: str
    is_active: bool


class RoleRead(BaseModel):
    slug: str
    name: str
    permissions: list[str] = Field(default_factory=list)
    users: list[RoleUserRead] = Field(default_factory=list)


class UserRead(BaseModel):
    id: int
    email: str
    display_name: str
    is_active: bool
    is_superuser: bool
    roles: list[str]


class UserCreate(BaseModel):
    email: str
    display_name: str
    password: str
    role_slugs: list[str] = Field(default_factory=list)
    is_active: bool = True
    is_superuser: bool = False


class UserActiveUpdate(BaseModel):
    is_active: bool


class UserRolesUpdate(BaseModel):
    role_slugs: list[str] = Field(default_factory=list)


class UserPasswordReset(BaseModel):
    password: str


@router.get(
    "/admin/status",
    response_model=AdminStatus,
    dependencies=[Depends(require_permission("core.admin"))],
)
def admin_status() -> AdminStatus:
    return AdminStatus(status="ok")


@router.get(
    "/admin/roles",
    response_model=list[RoleRead],
    dependencies=[Depends(require_permission("core.admin"))],
)
def list_roles(db: Session = Depends(get_db)) -> list[RoleRead]:
    roles = db.scalars(
        select(Role)
        .options(selectinload(Role.permissions), selectinload(Role.users))
        .order_by(Role.slug)
    ).all()
    return [_role_read(role) for role in roles]


@router.get(
    "/admin/users",
    response_model=list[UserRead],
    dependencies=[Depends(require_permission("core.admin"))],
)
def list_users(db: Session = Depends(get_db)) -> list[UserRead]:
    users = db.scalars(select(User).order_by(User.email)).unique().all()
    return [_user_read(user) for user in users]


@router.post("/admin/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("core.admin")),
) -> UserRead:
    email = payload.email.strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required")
    if not payload.display_name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Display name is required")
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

    password_errors = validate_password_policy(payload.password)
    if password_errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=password_errors)

    roles = _roles_for_slugs(db, payload.role_slugs)
    user = User(
        email=email,
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
        is_superuser=payload.is_superuser,
        roles=roles,
    )
    db.add(user)
    db.flush()
    record_audit_event(
        db,
        action="users.created",
        target_type="user",
        target_id=str(user.id),
        outcome="success",
        actor_user_id=actor.id,
        metadata={"email": user.email, "roles": ",".join(sorted(payload.role_slugs))},
    )
    db.commit()
    db.refresh(user)
    return _user_read(user)


@router.patch("/admin/users/{user_id}/active", response_model=UserRead)
def update_user_active_status(
    user_id: int,
    payload: UserActiveUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("core.admin")),
) -> UserRead:
    user = _get_user_or_404(db, user_id)
    previous_value = user.is_active
    user.is_active = payload.is_active
    record_audit_event(
        db,
        action="users.active_status.updated",
        target_type="user",
        target_id=str(user.id),
        outcome="success",
        actor_user_id=actor.id,
        metadata={"previous": str(previous_value), "is_active": str(user.is_active)},
    )
    db.commit()
    db.refresh(user)
    return _user_read(user)


@router.patch("/admin/users/{user_id}/roles", response_model=UserRead)
def update_user_roles(
    user_id: int,
    payload: UserRolesUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("core.admin")),
) -> UserRead:
    user = _get_user_or_404(db, user_id)
    previous_roles = sorted(role.slug for role in user.roles)
    user.roles = _roles_for_slugs(db, payload.role_slugs)
    record_audit_event(
        db,
        action="users.roles.updated",
        target_type="user",
        target_id=str(user.id),
        outcome="success",
        actor_user_id=actor.id,
        metadata={"previous_roles": ",".join(previous_roles), "roles": ",".join(sorted(payload.role_slugs))},
    )
    db.commit()
    db.refresh(user)
    return _user_read(user)


@router.patch("/admin/users/{user_id}/password", response_model=UserRead)
def reset_user_password(
    user_id: int,
    payload: UserPasswordReset,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("core.admin")),
) -> UserRead:
    user = _get_user_or_404(db, user_id)
    password_errors = validate_password_policy(payload.password)
    if password_errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=password_errors)

    user.password_hash = hash_password(payload.password)
    record_audit_event(
        db,
        action="users.password_reset",
        target_type="user",
        target_id=str(user.id),
        outcome="success",
        actor_user_id=actor.id,
    )
    db.commit()
    db.refresh(user)
    return _user_read(user)


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _roles_for_slugs(db: Session, role_slugs: list[str]) -> list[Role]:
    unique_slugs = sorted(set(role_slugs))
    if not unique_slugs:
        return []

    roles = db.scalars(select(Role).where(Role.slug.in_(unique_slugs))).all()
    found_slugs = {role.slug for role in roles}
    missing_slugs = [role_slug for role_slug in unique_slugs if role_slug not in found_slugs]
    if missing_slugs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown roles: {', '.join(missing_slugs)}",
        )
    return list(roles)


def _user_read(user: User) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        roles=sorted(role.slug for role in user.roles),
    )


def _role_read(role: Role) -> RoleRead:
    users = sorted(role.users, key=lambda user: user.email)
    return RoleRead(
        slug=role.slug,
        name=role.name,
        permissions=sorted(permission.slug for permission in role.permissions),
        users=[
            RoleUserRead(
                id=user.id,
                email=user.email,
                display_name=user.display_name,
                is_active=user.is_active,
            )
            for user in users
        ],
    )
