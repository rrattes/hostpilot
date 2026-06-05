from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit.events import record_audit_event
from app.core.auth.dependencies import get_current_user
from app.core.rbac.permissions import require_permission
from app.db.models import Setting, User
from app.db.session import get_db


router = APIRouter()


class SettingRead(BaseModel):
    key: str
    value: str
    is_sensitive: bool


class SettingUpdate(BaseModel):
    value: str


@router.get(
    "/settings",
    response_model=list[SettingRead],
    dependencies=[Depends(require_permission("settings.view"))],
)
def list_settings(db: Session = Depends(get_db)) -> list[SettingRead]:
    settings = db.scalars(select(Setting).order_by(Setting.key)).all()
    return [_setting_read(setting) for setting in settings]


@router.get(
    "/settings/{key}",
    response_model=SettingRead,
    dependencies=[Depends(require_permission("settings.view"))],
)
def get_setting(key: str, db: Session = Depends(get_db)) -> SettingRead:
    setting = db.scalar(select(Setting).where(Setting.key == key))
    if setting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setting not found")
    return _setting_read(setting)


@router.patch(
    "/settings/{key}",
    response_model=SettingRead,
    dependencies=[Depends(require_permission("settings.edit"))],
)
def update_setting(
    key: str,
    payload: SettingUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SettingRead:
    setting = db.scalar(select(Setting).where(Setting.key == key))
    if setting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Setting not found")

    previous_value = setting.value
    setting.value = payload.value
    record_audit_event(
        db,
        action="settings.updated",
        target_type="setting",
        target_id=setting.key,
        outcome="success",
        actor_user_id=user.id,
        metadata={"previous_value": previous_value},
    )
    db.commit()
    db.refresh(setting)
    return _setting_read(setting)


def _setting_read(setting: Setting) -> SettingRead:
    return SettingRead(
        key=setting.key,
        value="" if setting.is_sensitive else setting.value,
        is_sensitive=setting.is_sensitive,
    )
