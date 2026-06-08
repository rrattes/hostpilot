from fastapi import FastAPI

from app.api.admin import router as admin_router
from app.api.agent import router as agent_router
from app.api.audit import router as audit_router
from app.api.auth import router as auth_router
from app.api.backups import router as backups_router
from app.api.core_status import router as core_status_router
from app.api.jobs import router as jobs_router
from app.api.modules import router as modules_router
from app.api.notifications import router as notifications_router
from app.api.servers import router as servers_router
from app.api.settings import router as settings_router
from app.core.auth.security import get_secret_key


get_secret_key()

app = FastAPI(
    title="HostPilot Core API",
    description="Neutral local server management platform core.",
    version="0.1.0",
)


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth_router, prefix="/api/core", tags=["auth"])
app.include_router(admin_router, prefix="/api/core", tags=["core"])
app.include_router(audit_router, prefix="/api/core", tags=["audit"])
app.include_router(backups_router, prefix="/api/core", tags=["backups"])
app.include_router(core_status_router, prefix="/api/core", tags=["core"])
app.include_router(jobs_router, prefix="/api/core", tags=["jobs"])
app.include_router(modules_router, prefix="/api/core", tags=["core"])
app.include_router(notifications_router, prefix="/api/core", tags=["notifications"])
app.include_router(servers_router, prefix="/api/core", tags=["servers"])
app.include_router(settings_router, prefix="/api/core", tags=["settings"])
app.include_router(agent_router, prefix="/api/agent", tags=["agent"])
