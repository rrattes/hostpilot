from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.rbac.permissions import require_permission
from app.db.models import Module
from app.db.session import get_db


router = APIRouter()


SectionStatus = Literal["unavailable", "coming_soon"]


class WebSectionStatus(BaseModel):
    slug: str
    name: str
    status: SectionStatus
    description: str
    action_label: str
    action_available: bool


class WebStatusRead(BaseModel):
    module_slug: str
    module_state: str
    enabled: bool
    operational: bool
    sections: list[WebSectionStatus]


WEB_SECTIONS = [
    WebSectionStatus(
        slug="sites",
        name="Sites",
        status="coming_soon",
        description="Website records and lifecycle workflows are not active in this scaffold.",
        action_label="Site creation coming soon",
        action_available=False,
    ),
    WebSectionStatus(
        slug="nginx",
        name="Nginx",
        status="unavailable",
        description="Nginx configuration checks and file edits are intentionally disabled.",
        action_label="Nginx actions unavailable",
        action_available=False,
    ),
    WebSectionStatus(
        slug="ssl",
        name="SSL",
        status="coming_soon",
        description="Certificate requests, renewals, and automation are not implemented.",
        action_label="SSL automation coming soon",
        action_available=False,
    ),
    WebSectionStatus(
        slug="logs",
        name="Logs",
        status="coming_soon",
        description="Web log browsing and retention controls are placeholder-only.",
        action_label="Log viewer coming soon",
        action_available=False,
    ),
    WebSectionStatus(
        slug="php-runtime",
        name="PHP Runtime",
        status="unavailable",
        description="PHP version and pool management are outside this scaffold.",
        action_label="PHP controls unavailable",
        action_available=False,
    ),
]


@router.get(
    "/web/status",
    response_model=WebStatusRead,
    dependencies=[Depends(require_permission("web.view"))],
)
def get_web_status(db: Session = Depends(get_db)) -> WebStatusRead:
    module = db.scalar(select(Module).where(Module.slug == "web"))
    module_state = module.state if module is not None else "available"
    enabled = module.enabled if module is not None else False

    return WebStatusRead(
        module_slug="web",
        module_state=module_state,
        enabled=enabled,
        operational=False,
        sections=WEB_SECTIONS,
    )
