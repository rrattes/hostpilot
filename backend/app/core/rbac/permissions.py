from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit.events import record_audit_event
from app.core.auth.dependencies import get_current_user
from app.core.notifications.events import create_notification
from app.db.models import Permission, Role, User
from app.db.session import get_db


def get_user_permission_slugs(db: Session, user: User) -> set[str]:
    rows = db.execute(
        select(Permission.slug)
        .join(Role.permissions)
        .join(Role.users)
        .where(User.id == user.id)
    )
    return {row[0] for row in rows}


def get_user_role_slugs(db: Session, user: User) -> set[str]:
    rows = db.execute(select(Role.slug).join(Role.users).where(User.id == user.id))
    return {row[0] for row in rows}


def require_permission(permission: str) -> Callable[..., User]:
    def dependency(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        permissions = get_user_permission_slugs(db, user)
        if permission in permissions:
            return user

        record_audit_event(
            db,
            action="rbac.access_denied",
            target_type="permission",
            target_id=permission,
            outcome="failure",
            actor_user_id=user.id,
            metadata={"email": user.email},
        )
        create_notification(
            db,
            title="Access denied",
            message=f"Access denied for permission {permission}.",
            severity="warning",
            user_id=user.id,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")

    return dependency
