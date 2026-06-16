import json
import logging
from time import perf_counter
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.agent_gateway.contracts import AgentActionRequest, AgentActionResponse
from app.core.agent_gateway.local_client import (
    LocalAgentTransportError,
    execute_local_agent_action,
    get_local_agent_health,
)
from app.core.agent_gateway.mock_client import allowed_mock_actions, run_mock_action
from app.core.audit.events import record_audit_event
from app.core.auth.security import DEV_TEST_ENVIRONMENTS, dev_actions_enabled, get_runtime_environment
from app.core.notifications.events import create_notification
from app.db.models import Job, User


logger = logging.getLogger(__name__)


def get_agent_status() -> dict[str, object]:
    fallback_enabled = _dev_agent_fallback_enabled()
    try:
        health = get_local_agent_health()
        local_status = str(health.get("status", "ok"))
        is_connected = local_status == "ok"
        status = "connected" if is_connected else "unavailable"
        return {
            "status": status,
            "mode": str(health.get("mode", "local-http")),
            "allowed_actions": list(health.get("allowed_actions", allowed_mock_actions())),
            "using_real_agent": is_connected,
            "using_fallback": False,
            "fallback_enabled": fallback_enabled,
            "web_actions_use_real_agent": is_connected,
            "dev_actions_enabled": dev_actions_enabled(),
            "message": "Local Agent is connected." if is_connected else "Local Agent responded unhealthy.",
        }
    except LocalAgentTransportError as exc:
        if fallback_enabled:
            logger.warning("Local agent unavailable; using dev mock fallback: %s", exc)
            return {
                "status": "fallback",
                "mode": "mock-fallback",
                "allowed_actions": allowed_mock_actions(),
                "using_real_agent": False,
                "using_fallback": True,
                "fallback_enabled": True,
                "web_actions_use_real_agent": False,
                "dev_actions_enabled": dev_actions_enabled(),
                "message": "Local Agent is unavailable; Windows/dev mock fallback is active.",
            }
        logger.error("Local agent unavailable and fallback disabled: %s", exc)
        return {
            "status": "unavailable",
            "mode": "local-http",
            "allowed_actions": allowed_mock_actions(),
            "using_real_agent": False,
            "using_fallback": False,
            "fallback_enabled": False,
            "web_actions_use_real_agent": False,
            "dev_actions_enabled": dev_actions_enabled(),
            "message": "Local Agent is unavailable and fallback is disabled.",
        }


def _dev_agent_fallback_enabled() -> bool:
    return get_runtime_environment() in DEV_TEST_ENVIRONMENTS


def execute_mock_agent_action(
    db: Session,
    *,
    action: str,
    payload: dict[str, object],
    user: User,
) -> tuple[Job, AgentActionResponse]:
    request_id = str(uuid4())
    started_at = perf_counter()
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

    request = AgentActionRequest(
        action=action,
        payload=payload,
        requested_by=user.email,
        request_id=request_id,
    )
    if action not in allowed_mock_actions():
        response = run_mock_action(request)
    else:
        try:
            response = execute_local_agent_action(request)
        except LocalAgentTransportError as exc:
            if _dev_agent_fallback_enabled():
                logger.warning(
                    "Local agent unavailable for request_id=%s; using dev mock fallback: %s",
                    request_id,
                    exc,
                )
                response = run_mock_action(request)
            else:
                logger.error(
                    "Local agent unavailable for request_id=%s and fallback disabled: %s",
                    request_id,
                    exc,
                )
                response = AgentActionResponse(
                    success=False,
                    status="failed",
                    data={},
                    error="Local agent service is unavailable.",
                    duration_ms=int((perf_counter() - started_at) * 1000),
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
