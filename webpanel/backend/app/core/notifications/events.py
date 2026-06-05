from sqlalchemy.orm import Session

from app.db.models import Notification


def create_notification(
    db: Session,
    *,
    title: str,
    message: str,
    severity: str = "info",
    user_id: int | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        severity=severity,
        status="unread",
    )
    db.add(notification)
    return notification
