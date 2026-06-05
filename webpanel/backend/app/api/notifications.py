from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.auth.dependencies import get_current_user
from app.core.rbac.permissions import require_permission
from app.db.models import Notification, User
from app.db.session import get_db


router = APIRouter()


class NotificationRead(BaseModel):
    id: int
    title: str
    message: str
    status: str
    severity: str
    created_at: datetime
    updated_at: datetime


class NotificationList(BaseModel):
    items: list[NotificationRead]
    unread_count: int
    total: int
    limit: int
    offset: int


@router.get(
    "/notifications",
    response_model=NotificationList,
    dependencies=[Depends(require_permission("notifications.view"))],
)
def list_notifications(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> NotificationList:
    base = select(Notification).where(_visible_to_user(user))
    if status_filter:
        base = base.where(Notification.status == status_filter)

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    unread_count = (
        db.scalar(
            select(func.count()).where(_visible_to_user(user), Notification.status == "unread")
        )
        or 0
    )
    items = db.scalars(
        base.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
    ).all()

    return NotificationList(
        items=[_notification_read(item) for item in items],
        unread_count=unread_count,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=NotificationRead,
    dependencies=[Depends(require_permission("notifications.manage_own"))],
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationRead:
    notification = db.get(Notification, notification_id)
    if notification is None or not _can_manage(user, notification):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notification.status = "read"
    db.commit()
    db.refresh(notification)
    return _notification_read(notification)


@router.patch(
    "/notifications/read-all",
    response_model=NotificationList,
    dependencies=[Depends(require_permission("notifications.manage_own"))],
)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationList:
    notifications = db.scalars(select(Notification).where(_visible_to_user(user))).all()
    for notification in notifications:
        notification.status = "read"
    db.commit()
    return list_notifications(db=db, user=user, status_filter=None, limit=20, offset=0)


def _visible_to_user(user: User):
    return or_(Notification.user_id == user.id, Notification.user_id.is_(None))


def _can_manage(user: User, notification: Notification) -> bool:
    return notification.user_id in {None, user.id}


def _notification_read(notification: Notification) -> NotificationRead:
    return NotificationRead(
        id=notification.id,
        title=notification.title,
        message=notification.message,
        status=notification.status,
        severity=notification.severity,
        created_at=notification.created_at,
        updated_at=notification.updated_at,
    )
