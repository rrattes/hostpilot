from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit.events import record_audit_event
from app.core.auth.dependencies import get_current_user
from app.core.rbac.permissions import require_permission
from app.db.models import Server, User
from app.db.session import get_db


router = APIRouter()


class ServerRead(BaseModel):
    slug: str
    name: str
    description: str
    hostname: str
    os_name: str
    is_local: bool


class ServerUpdate(BaseModel):
    name: str
    description: str = ""


@router.get(
    "/server/local",
    response_model=ServerRead,
    dependencies=[Depends(require_permission("core.view"))],
)
def get_local_server(db: Session = Depends(get_db)) -> ServerRead:
    server = _local_server(db)
    return _server_read(server)


@router.patch(
    "/server/local",
    response_model=ServerRead,
    dependencies=[Depends(require_permission("settings.edit"))],
)
def update_local_server(
    payload: ServerUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ServerRead:
    server = _local_server(db)
    previous_name = server.name
    previous_description = server.description
    server.name = payload.name
    server.description = payload.description
    record_audit_event(
        db,
        action="server.display.updated",
        target_type="server",
        target_id=server.slug,
        outcome="success",
        actor_user_id=user.id,
        metadata={"previous_name": previous_name, "previous_description": previous_description},
    )
    db.commit()
    db.refresh(server)
    return _server_read(server)


def _local_server(db: Session) -> Server:
    server = db.scalar(select(Server).where(Server.slug == "local"))
    if server is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local server not found")
    return server


def _server_read(server: Server) -> ServerRead:
    return ServerRead(
        slug=server.slug,
        name=server.name,
        description=server.description,
        hostname=server.hostname,
        os_name=server.os_name,
        is_local=server.is_local,
    )
