from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.rbac.permissions import require_permission
from app.db.models import User


router = APIRouter()


class AdminStatus(BaseModel):
    status: str


@router.get(
    "/admin/status",
    response_model=AdminStatus,
    dependencies=[Depends(require_permission("core.admin"))],
)
def admin_status() -> AdminStatus:
    return AdminStatus(status="ok")
