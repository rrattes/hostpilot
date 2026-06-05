from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.rbac.permissions import require_permission
from app.db.models import AuditEvent
from app.db.session import get_db


router = APIRouter()


class AuditEventRead(BaseModel):
    id: int
    actor_user_id: int | None
    action: str
    target_type: str
    target_id: str | None
    outcome: str
    metadata: str
    created_at: datetime


class AuditEventList(BaseModel):
    items: list[AuditEventRead]
    total: int
    limit: int
    offset: int


def _audit_event_read(event: AuditEvent) -> AuditEventRead:
    return AuditEventRead(
        id=event.id,
        actor_user_id=event.actor_user_id,
        action=event.action,
        target_type=event.target_type,
        target_id=event.target_id,
        outcome=event.outcome,
        metadata=event.metadata_json,
        created_at=event.created_at,
    )


@router.get(
    "/audit/events",
    response_model=AuditEventList,
    dependencies=[Depends(require_permission("audit.view"))],
)
def list_audit_events(
    db: Session = Depends(get_db),
    user: int | None = None,
    action: str | None = None,
    status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> AuditEventList:
    statement = select(AuditEvent)

    if user is not None:
        statement = statement.where(AuditEvent.actor_user_id == user)
    if action:
        statement = statement.where(AuditEvent.action == action)
    if status:
        statement = statement.where(AuditEvent.outcome == status)
    if date_from is not None:
        statement = statement.where(AuditEvent.created_at >= date_from)
    if date_to is not None:
        statement = statement.where(AuditEvent.created_at <= date_to)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    events = db.scalars(
        statement.order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)
    ).all()

    return AuditEventList(
        items=[_audit_event_read(event) for event in events],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/audit/events/{event_id}",
    response_model=AuditEventRead,
    dependencies=[Depends(require_permission("audit.view"))],
)
def get_audit_event(event_id: int, db: Session = Depends(get_db)) -> AuditEventRead:
    event = db.get(AuditEvent, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit event not found")
    return _audit_event_read(event)
