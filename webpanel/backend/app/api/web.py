from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit.events import record_audit_event
from app.core.auth.dependencies import get_current_user
from app.core.rbac.permissions import require_permission
from app.db.models import Module, User, WebSite
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


class WebSiteRead(BaseModel):
    id: int
    domain: str
    root_path: str
    status: str
    php_runtime: str
    ssl_enabled: bool
    created_at: datetime
    updated_at: datetime


class WebSiteCreate(BaseModel):
    domain: str = Field(min_length=1, max_length=255)
    root_path: str = Field(min_length=1)
    php_runtime: str = Field(default="none", min_length=1, max_length=80)
    ssl_enabled: bool = False


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


@router.get(
    "/web/sites",
    response_model=list[WebSiteRead],
    dependencies=[Depends(require_permission("web.sites.view"))],
)
def list_web_sites(db: Session = Depends(get_db)) -> list[WebSiteRead]:
    sites = db.scalars(select(WebSite).order_by(WebSite.domain)).all()
    return [_site_read(site) for site in sites]


@router.get(
    "/web/sites/{site_id}",
    response_model=WebSiteRead,
    dependencies=[Depends(require_permission("web.sites.view"))],
)
def get_web_site(site_id: int, db: Session = Depends(get_db)) -> WebSiteRead:
    return _site_read(_site_or_404(db, site_id))


@router.post(
    "/web/sites",
    response_model=WebSiteRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("web.sites.manage"))],
)
def create_web_site(
    payload: WebSiteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WebSiteRead:
    domain = payload.domain.strip().lower()
    root_path = payload.root_path.strip()
    php_runtime = payload.php_runtime.strip()
    if not domain or not root_path or not php_runtime:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Domain, root path, and PHP runtime are required.",
        )

    existing = db.scalar(select(WebSite).where(WebSite.domain == domain))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Site domain already exists")

    site = WebSite(
        domain=domain,
        root_path=root_path,
        status="config_pending",
        php_runtime=php_runtime,
        ssl_enabled=payload.ssl_enabled,
    )
    db.add(site)
    db.flush()
    record_audit_event(
        db,
        action="web.site.created",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={
            "domain": site.domain,
            "status": site.status,
            "provisioning": "not_provisioned",
        },
    )
    db.commit()
    db.refresh(site)
    return _site_read(site)


@router.patch(
    "/web/sites/{site_id}/disable",
    response_model=WebSiteRead,
    dependencies=[Depends(require_permission("web.sites.manage"))],
)
def disable_web_site(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WebSiteRead:
    site = _site_or_404(db, site_id)
    previous_status = site.status
    site.status = "disabled"
    record_audit_event(
        db,
        action="web.site.disabled",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={
            "domain": site.domain,
            "previous_status": previous_status,
            "provisioning": "record_only",
        },
    )
    db.commit()
    db.refresh(site)
    return _site_read(site)


def _site_or_404(db: Session, site_id: int) -> WebSite:
    site = db.get(WebSite, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Web site not found")
    return site


def _site_read(site: WebSite) -> WebSiteRead:
    return WebSiteRead(
        id=site.id,
        domain=site.domain,
        root_path=site.root_path,
        status=site.status,
        php_runtime=site.php_runtime,
        ssl_enabled=site.ssl_enabled,
        created_at=site.created_at,
        updated_at=site.updated_at,
    )
