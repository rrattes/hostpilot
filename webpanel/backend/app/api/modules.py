from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit.events import record_audit_event
from app.core.auth.dependencies import get_current_user
from app.core.rbac.permissions import require_permission
from app.db.models import Module, User
from app.db.session import get_db


router = APIRouter()


ModuleState = Literal["available", "installed", "enabled", "locked"]


class ModuleRead(BaseModel):
    slug: str
    name: str
    version: str
    state: ModuleState
    enabled: bool
    locked: bool
    installed: bool


class ModuleUpdate(BaseModel):
    state: ModuleState


@router.get(
    "/modules",
    response_model=list[ModuleRead],
    dependencies=[Depends(require_permission("modules.view"))],
)
def list_modules(db: Session = Depends(get_db)) -> list[ModuleRead]:
    modules = db.scalars(select(Module).order_by(Module.name)).all()
    return [
        ModuleRead(
            slug=module.slug,
            name=module.name,
            version=module.version,
            state=module.state,
            enabled=module.enabled,
            locked=module.locked,
            installed=module.installed,
        )
        for module in modules
    ]


@router.get(
    "/modules/{slug}",
    response_model=ModuleRead,
    dependencies=[Depends(require_permission("modules.view"))],
)
def get_module(slug: str, db: Session = Depends(get_db)) -> ModuleRead:
    module = db.scalar(select(Module).where(Module.slug == slug))
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    return _module_read(module)


@router.patch(
    "/modules/{slug}",
    response_model=ModuleRead,
    dependencies=[Depends(require_permission("modules.manage"))],
)
def update_module_state(
    slug: str,
    payload: ModuleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ModuleRead:
    module = db.scalar(select(Module).where(Module.slug == slug))
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    if module.slug == "core" and payload.state != "enabled":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Core must stay enabled")

    previous_state = module.state
    _apply_state(module, payload.state)
    record_audit_event(
        db,
        action="modules.state.updated",
        target_type="module",
        target_id=module.slug,
        outcome="success",
        actor_user_id=user.id,
        metadata={"previous_state": previous_state, "state": module.state},
    )
    db.commit()
    db.refresh(module)
    return _module_read(module)


def _module_read(module: Module) -> ModuleRead:
    return ModuleRead(
        slug=module.slug,
        name=module.name,
        version=module.version,
        state=module.state,  # type: ignore[arg-type]
        enabled=module.enabled,
        locked=module.locked,
        installed=module.installed,
    )


def _apply_state(module: Module, state: ModuleState) -> None:
    module.state = state
    module.enabled = state == "enabled"
    module.locked = state == "locked"
    module.installed = state in {"installed", "enabled"}
