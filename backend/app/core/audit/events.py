import json

from sqlalchemy.orm import Session

from app.db.models import AuditEvent


def record_audit_event(
    db: Session,
    *,
    action: str,
    target_type: str,
    outcome: str,
    actor_user_id: int | None = None,
    target_id: str | None = None,
    metadata: dict[str, str] | None = None,
) -> None:
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            outcome=outcome,
            metadata_json=json.dumps(metadata or {}),
        )
    )
