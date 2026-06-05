import json
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.agent_gateway.contracts import AgentActionRequest, AgentActionResponse
from app.core.agent_gateway.mock_client import allowed_mock_actions, run_mock_action
from app.core.audit.events import record_audit_event
from app.core.notifications.events import create_notification
from app.db.models import Job, User


def get_agent_status() -> dict[str, object]:
    return {
        "status": "ok",
        "mode": "mock",
        "allowed_actions": allowed_mock_actions(),
    }


def execute_mock_agent_action(
    db: Session,
    *,
    action: str,
    payload: dict[str, object],
    user: User,
) -> tuple[Job, AgentActionResponse]:
    request_id = str(uuid4())
    job = Job(
        type="agent_action",
        module="agent",
        action=action,
        status="queued",
        payload=json.dumps(
            {
                "action": action,
                "payload": payload,
                "requested_by": user.email,
                "request_id": request_id,
            }
        ),
    )
    db.add(job)
    db.flush()

    record_audit_event(
        db,
        action="agent.action.requested",
        target_type="job",
        target_id=str(job.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={"agent_action": action, "request_id": request_id},
    )

    response = run_mock_action(
        AgentActionRequest(
            action=action,
            payload=payload,
            requested_by=user.email,
            request_id=request_id,
        )
    )
    job.status = "completed" if response.success else "failed"
    job.result = json.dumps(
        {
            "success": response.success,
            "status": response.status,
            "data": response.data,
            "error": response.error,
            "duration_ms": response.duration_ms,
        }
    )

    record_audit_event(
        db,
        action="agent.action.completed",
        target_type="job",
        target_id=str(job.id),
        outcome="success" if response.success else "failure",
        actor_user_id=user.id,
        metadata={"agent_action": action, "request_id": request_id, "status": response.status},
    )
    create_notification(
        db,
        title="Mock agent job completed" if response.success else "Mock agent job failed",
        message=f"Agent action {action} {job.status}.",
        severity="info" if response.success else "error",
        user_id=user.id,
    )
    db.commit()
    db.refresh(job)

    return job, response
