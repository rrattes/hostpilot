from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit.events import record_audit_event
from app.core.auth.dependencies import get_current_user
from app.core.backups.service import CoreBackupError, create_core_backup
from app.core.rbac.permissions import require_permission
from app.db.models import CoreBackup, User
from app.db.session import get_db


router = APIRouter()


class CoreBackupRead(BaseModel):
    id: str
    created_at: datetime
    created_by: int | None
    status: str
    file_path: str
    size_bytes: int


def _backup_read(backup: CoreBackup) -> CoreBackupRead:
    return CoreBackupRead(
        id=backup.id,
        created_at=backup.created_at,
        created_by=backup.created_by,
        status=backup.status,
        file_path=backup.file_path,
        size_bytes=backup.size_bytes,
    )


@router.post(
    "/backups",
    response_model=CoreBackupRead,
    dependencies=[Depends(require_permission("core.backup.create"))],
)
def create_backup(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CoreBackupRead:
    backup: CoreBackup | None = None
    try:
        backup, included_files = create_core_backup(db, user)
        record_audit_event(
            db,
            action="core.backup.created",
            target_type="core_backup",
            target_id=backup.id,
            actor_user_id=user.id,
            outcome="success",
            metadata={"file_path": backup.file_path, "files": ",".join(included_files)},
        )
        db.commit()
        db.refresh(backup)
        return _backup_read(backup)
    except Exception as exc:
        reason = str(exc) if isinstance(exc, CoreBackupError) else "Core backup failed while writing archive."
        target_id = backup.id if backup is not None else getattr(exc, "backup_id", None)
        record_audit_event(
            db,
            action="core.backup.failed",
            target_type="core_backup",
            target_id=target_id,
            actor_user_id=user.id,
            outcome="failure",
            metadata={"reason": reason, "error_type": exc.__class__.__name__},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=reason,
        ) from exc


@router.get(
    "/backups",
    response_model=list[CoreBackupRead],
    dependencies=[Depends(require_permission("core.backup.view"))],
)
def list_backups(db: Session = Depends(get_db)) -> list[CoreBackupRead]:
    backups = db.scalars(select(CoreBackup).order_by(CoreBackup.created_at.desc())).all()
    return [_backup_read(backup) for backup in backups]
