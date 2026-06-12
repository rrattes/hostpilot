from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.agent_gateway.service import get_agent_status
from app.core.rbac.permissions import require_permission
from app.db.models import AuditEvent, Job, Module, Server
from app.db.session import get_db


router = APIRouter()


class ModuleStatus(BaseModel):
    slug: str
    name: str
    state: str


class LocalServerStatus(BaseModel):
    slug: str
    name: str
    description: str
    hostname: str
    os_name: str
    is_local: bool


class CoreStatus(BaseModel):
    product: str
    core_version: str
    core_status: Literal["ok"]
    database_status: Literal["ok", "error"]
    agent_status: Literal["connected", "fallback", "unavailable"]
    runtime: str
    database: str
    agent_mode: str
    agent_web_actions_use_real_agent: bool
    local_server: LocalServerStatus | None
    enabled_modules_count: int
    locked_modules_count: int
    recent_jobs_count: int
    recent_audit_events_count: int
    modules: list[ModuleStatus]
    generated_at: datetime


@router.get(
    "/status",
    response_model=CoreStatus,
    dependencies=[Depends(require_permission("core.view"))],
)
def get_core_status(db: Session = Depends(get_db)) -> CoreStatus:
    database_status: Literal["ok", "error"] = "ok"
    try:
        db.execute(text("select 1"))
    except Exception:
        database_status = "error"

    recent_since = datetime.now(UTC) - timedelta(hours=24)
    local_server = db.scalar(select(Server).where(Server.slug == "local"))
    modules = db.scalars(select(Module).order_by(Module.name)).all()
    agent_status = get_agent_status()

    return CoreStatus(
        product="HostPilot Core",
        core_version="0.1.0",
        core_status="ok",
        database_status=database_status,
        agent_status=str(agent_status["status"]),  # type: ignore[arg-type]
        runtime="FastAPI",
        database="SQLite",
        agent_mode=str(agent_status["mode"]),
        agent_web_actions_use_real_agent=bool(agent_status["web_actions_use_real_agent"]),
        local_server=_local_server_status(local_server) if local_server is not None else None,
        enabled_modules_count=db.scalar(select(func.count()).where(Module.state == "enabled")) or 0,
        locked_modules_count=db.scalar(select(func.count()).where(Module.state == "locked")) or 0,
        recent_jobs_count=db.scalar(select(func.count()).where(Job.created_at >= recent_since)) or 0,
        recent_audit_events_count=db.scalar(
            select(func.count()).where(AuditEvent.created_at >= recent_since)
        )
        or 0,
        modules=[
            ModuleStatus(slug=module.slug, name=module.name, state=module.state)
            for module in modules
        ],
        generated_at=datetime.now(UTC),
    )


def _local_server_status(server: Server) -> LocalServerStatus:
    return LocalServerStatus(
        slug=server.slug,
        name=server.name,
        description=server.description,
        hostname=server.hostname,
        os_name=server.os_name,
        is_local=server.is_local,
    )
