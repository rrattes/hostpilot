from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.agent_gateway.service import execute_mock_agent_action, get_agent_status
from app.core.auth.dependencies import get_current_user
from app.core.rbac.permissions import require_permission
from app.db.models import Job, User
from app.db.session import get_db


router = APIRouter()


class AgentStatus(BaseModel):
    status: Literal["connected", "fallback", "unavailable"]
    mode: str
    allowed_actions: list[str]
    using_real_agent: bool
    using_fallback: bool
    fallback_enabled: bool
    web_actions_use_real_agent: bool
    message: str


class AgentActionPayload(BaseModel):
    payload: dict[str, Any] = {}


class AgentActionResult(BaseModel):
    job_id: int
    success: bool
    status: str
    data: dict[str, Any]
    error: str | None
    duration_ms: int


class AgentJobRead(BaseModel):
    id: int
    action: str
    status: str
    result: str | None
    created_at: str


@router.get("/status", response_model=AgentStatus, dependencies=[Depends(require_permission("agent.view"))])
def agent_status() -> AgentStatus:
    return AgentStatus(**get_agent_status())


@router.post(
    "/actions/{action_name}",
    response_model=AgentActionResult,
    dependencies=[Depends(require_permission("agent.execute_mock"))],
)
def execute_action(
    action_name: str,
    payload: AgentActionPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentActionResult:
    job, response = execute_mock_agent_action(
        db,
        action=action_name,
        payload=payload.payload,
        user=user,
    )
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.error or "Agent action failed",
        )

    return AgentActionResult(
        job_id=job.id,
        success=response.success,
        status=response.status,
        data=response.data,
        error=response.error,
        duration_ms=response.duration_ms,
    )


@router.get("/jobs/recent", response_model=list[AgentJobRead], dependencies=[Depends(require_permission("agent.view"))])
def recent_agent_jobs(db: Session = Depends(get_db)) -> list[AgentJobRead]:
    jobs = db.scalars(
        select(Job).where(Job.module == "agent").order_by(Job.created_at.desc()).limit(10)
    ).all()
    return [
        AgentJobRead(
            id=job.id,
            action=job.action,
            status=job.status,
            result=job.result,
            created_at=job.created_at.isoformat(),
        )
        for job in jobs
    ]
