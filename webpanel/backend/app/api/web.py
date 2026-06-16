from datetime import datetime
import posixpath
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.agent_gateway.service import execute_mock_agent_action, get_agent_status
from app.core.audit.events import record_audit_event
from app.core.auth.dependencies import get_current_user
from app.core.rbac.permissions import require_permission
from app.db.models import Module, Setting, User, WebSite
from app.db.session import get_db


router = APIRouter()


SectionStatus = Literal["available", "unavailable", "coming_soon"]
ProvisioningStatus = Literal["draft", "config_previewed", "ready_to_apply", "disabled", "error"]
DEFAULT_WEB_SITES_BASE_PATH = "/var/www/hostpilot-sites"
DEFAULT_WEB_LOG_BASE_PATH = "/var/log/nginx/hostpilot"
HOSTPILOT_NGINX_CONFIG_BASE_PATH = "/etc/nginx/sites-available/hostpilot"
NGINX_VALIDATION_COMMAND = "nginx -t"
NGINX_RELOAD_COMMAND = "systemctl reload nginx"
MAX_WEB_LOG_LINES = 500
MAX_WEB_FILE_PAGE_SIZE = 100
DANGEROUS_ROOT_PATHS = {"/", "/bin", "/etc", "/home", "/usr", "/var"}
DOMAIN_PATTERN = re.compile(
    r"^(?=.{1,253}$)(?!-)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


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
    provisioning_status: ProvisioningStatus
    php_runtime: str
    ssl_enabled: bool
    created_at: datetime
    updated_at: datetime


class WebSiteCreate(BaseModel):
    domain: str = Field(min_length=1, max_length=255)
    root_path: str = Field(min_length=1)
    php_runtime: str = Field(default="none", min_length=1, max_length=80)
    ssl_enabled: bool = False


class WebSiteUpdate(BaseModel):
    domain: str = Field(min_length=1, max_length=255)
    root_path: str = Field(min_length=1)
    php_runtime: str = Field(default="none", min_length=1, max_length=80)
    ssl_enabled: bool = False


class WebSiteNginxPreviewRead(BaseModel):
    site_id: int
    domain: str
    config: str
    saved: bool = False


class WebSiteReadinessCheck(BaseModel):
    slug: str
    label: str
    passed: bool
    detail: str


class WebSiteReadinessRead(BaseModel):
    site_id: int
    domain: str
    provisioning_status: ProvisioningStatus
    ready: bool
    checks: list[WebSiteReadinessCheck]


class WebSitePreflightCheck(BaseModel):
    slug: str
    label: str
    passed: bool
    detail: str


class WebSitePreflightRead(BaseModel):
    site_id: int
    domain: str
    ready: bool
    agent_status: str
    agent_mode: str
    using_real_agent: bool
    using_fallback: bool
    required_agent_actions: list[str]
    allowed_agent_actions: list[str]
    allowed_web_base_path: str
    nginx_config_base_path: str
    nginx_validation_command: str
    reload_command: str
    checks: list[WebSitePreflightCheck]


class WebSiteNginxApplyPlanRead(BaseModel):
    site_id: int
    domain: str
    target_config_path: str
    webroot_path: str
    required_directories: list[str]
    config_filename: str
    validation_commands: list[str]
    service_reload_command: str
    risk_level: str
    confirmation_phrase: str
    plan_only: bool = True


class WebSiteDryRunRequest(BaseModel):
    confirmation_phrase: str = Field(min_length=1)


class WebSiteDryRunRead(BaseModel):
    site_id: int
    domain: str
    config_content: str
    target_config_path: str
    webroot_path: str
    directory_checks: list[str]
    nginx_validation_command: str
    reload_command: str
    expected_result: str
    executed: bool = False
    wrote_files: bool = False


class WebSiteApplyRequest(BaseModel):
    confirmation_phrase: str = Field(min_length=1)


class WebSiteApplyRead(BaseModel):
    site: WebSiteRead
    job_id: int
    success: bool
    status: str
    result: dict[str, object]
    error: str | None


class WebSiteDisableRequest(BaseModel):
    confirmation_phrase: str = Field(min_length=1)


class WebSiteDisableRead(BaseModel):
    site: WebSiteRead
    job_id: int
    success: bool
    status: str
    result: dict[str, object]
    error: str | None


class WebSiteReapplyRequest(BaseModel):
    confirmation_phrase: str = Field(min_length=1)


class WebSiteReapplyRead(BaseModel):
    site: WebSiteRead
    job_id: int
    success: bool
    status: str
    result: dict[str, object]
    error: str | None


class WebSiteLogFileRead(BaseModel):
    path: str
    missing: bool
    lines: list[str]


class WebSiteLogsRead(BaseModel):
    site_id: int
    domain: str
    line_limit: int
    job_id: int
    status: str
    access: WebSiteLogFileRead
    error: WebSiteLogFileRead


class WebSiteFileEntryRead(BaseModel):
    name: str
    type: Literal["directory", "file"]
    size: int
    modified_at: float
    relative_path: str


class WebSiteFilesRead(BaseModel):
    site_id: int
    domain: str
    root_path: str
    relative_subpath: str
    target_path: str
    page: int
    page_size: int
    max_depth: int
    total_entries: int
    has_next: bool
    status: str
    job_id: int
    entries: list[WebSiteFileEntryRead]


WEB_SECTIONS = [
    WebSectionStatus(
        slug="sites",
        name="Sites",
        status="available",
        description="Create site records and open Files, Logs, and Nginx workflows from each site row.",
        action_label="Create or select a site record",
        action_available=True,
    ),
    WebSectionStatus(
        slug="nginx",
        name="Nginx",
        status="available",
        description="Preview, plan, dry-run, apply, disable, and re-apply controlled HostPilot configs.",
        action_label="Use Nginx actions from a site row",
        action_available=True,
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
        status="available",
        description="Read-only recent access and error log tails are available per site.",
        action_label="Open logs from a site row",
        action_available=True,
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
        operational=True,
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


@router.get(
    "/web/sites/{site_id}/logs",
    response_model=WebSiteLogsRead,
    dependencies=[Depends(require_permission("web.sites.view"))],
)
def get_web_site_logs(
    site_id: int,
    lines: int = Query(default=100, ge=1, le=MAX_WEB_LOG_LINES),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WebSiteLogsRead:
    site = _site_or_404(db, site_id)
    agent_payload = _agent_logs_payload(site, lines)
    record_audit_event(
        db,
        action="web.site.logs.accessed",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={"domain": site.domain, "line_limit": str(lines), "read_only": "true"},
    )
    job, response = execute_mock_agent_action(
        db,
        action="web.logs.tail_site_logs",
        payload=agent_payload,
        user=user,
    )
    if not response.success:
        record_audit_event(
            db,
            action="web.site.logs.access_failed",
            target_type="web_site",
            target_id=str(site.id),
            outcome="failure",
            actor_user_id=user.id,
            metadata={"domain": site.domain, "agent_status": response.status},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=response.error or "Unable to read Web site logs.",
        )

    logs = response.data.get("logs", {})
    access_log = logs.get("access", {}) if isinstance(logs, dict) else {}
    error_log = logs.get("error", {}) if isinstance(logs, dict) else {}
    db.commit()
    db.refresh(job)
    return WebSiteLogsRead(
        site_id=site.id,
        domain=site.domain,
        line_limit=int(response.data.get("line_limit", lines)),
        job_id=job.id,
        status=response.status,
        access=_log_file_read(access_log),
        error=_log_file_read(error_log),
    )


@router.get(
    "/web/sites/{site_id}/files",
    response_model=WebSiteFilesRead,
    dependencies=[Depends(require_permission("web.sites.view"))],
)
def get_web_site_files(
    site_id: int,
    subpath: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=MAX_WEB_FILE_PAGE_SIZE),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WebSiteFilesRead:
    site = _site_or_404(db, site_id)
    _validate_root_path(site.root_path, _allowed_base_path(db))
    relative_subpath = _validate_relative_subpath(subpath)
    allowed_base_path = _allowed_base_path(db)
    agent_payload = _agent_files_payload(site, relative_subpath, page, page_size, allowed_base_path)
    record_audit_event(
        db,
        action="web.site.files.listed",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={
            "domain": site.domain,
            "relative_subpath": relative_subpath,
            "page": str(page),
            "page_size": str(page_size),
            "read_only": "true",
        },
    )
    job, response = execute_mock_agent_action(
        db,
        action="web.files.list_site_files",
        payload=agent_payload,
        user=user,
    )
    if not response.success:
        record_audit_event(
            db,
            action="web.site.files.list_failed",
            target_type="web_site",
            target_id=str(site.id),
            outcome="failure",
            actor_user_id=user.id,
            metadata={"domain": site.domain, "agent_status": response.status},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=response.error or "Unable to list Web site files.",
        )

    db.commit()
    db.refresh(job)
    return WebSiteFilesRead(
        site_id=site.id,
        domain=site.domain,
        root_path=str(response.data.get("root_path", site.root_path)),
        relative_subpath=str(response.data.get("relative_subpath", relative_subpath)),
        target_path=str(response.data.get("target_path", site.root_path)),
        page=int(response.data.get("page", page)),
        page_size=int(response.data.get("page_size", page_size)),
        max_depth=int(response.data.get("max_depth", 1)),
        total_entries=int(response.data.get("total_entries", 0)),
        has_next=bool(response.data.get("has_next", False)),
        status=str(response.data.get("status", response.status)),
        job_id=job.id,
        entries=_file_entries_read(response.data.get("entries", [])),
    )


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
    domain = _validate_domain(payload.domain)
    root_path = _validate_root_path(payload.root_path, _allowed_base_path(db))
    php_runtime = payload.php_runtime.strip()
    if not php_runtime:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PHP runtime is required.",
        )

    existing = db.scalar(select(WebSite).where(WebSite.domain == domain))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Site domain already exists")

    site = WebSite(
        domain=domain,
        root_path=root_path,
        status="config_pending",
        provisioning_status="draft",
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
    "/web/sites/{site_id}",
    response_model=WebSiteRead,
    dependencies=[Depends(require_permission("web.sites.manage"))],
)
def update_web_site(
    site_id: int,
    payload: WebSiteUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WebSiteRead:
    site = _site_or_404(db, site_id)
    domain = _validate_domain(payload.domain)
    root_path = _validate_root_path(payload.root_path, _allowed_base_path(db))
    php_runtime = payload.php_runtime.strip()
    if not php_runtime:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PHP runtime is required.",
        )

    existing = db.scalar(select(WebSite).where(WebSite.domain == domain, WebSite.id != site.id))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Site domain already exists")

    previous_domain = site.domain
    previous_root_path = site.root_path
    site.domain = domain
    site.root_path = root_path
    site.php_runtime = php_runtime
    site.ssl_enabled = payload.ssl_enabled
    if site.provisioning_status not in {"disabled", "error"}:
        site.provisioning_status = "draft"
    record_audit_event(
        db,
        action="web.site.updated",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={
            "domain": site.domain,
            "previous_domain": previous_domain,
            "previous_root_path": previous_root_path,
            "provisioning": "record_only",
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
    previous_provisioning_status = site.provisioning_status
    site.status = "disabled"
    site.provisioning_status = "disabled"
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
            "previous_provisioning_status": previous_provisioning_status,
            "provisioning": "record_only",
        },
    )
    db.commit()
    db.refresh(site)
    return _site_read(site)


@router.get(
    "/web/sites/{site_id}/nginx-preview",
    response_model=WebSiteNginxPreviewRead,
    dependencies=[Depends(require_permission("web.sites.view"))],
)
def preview_web_site_nginx_config(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WebSiteNginxPreviewRead:
    site = _site_or_404(db, site_id)
    config = _nginx_preview(site)
    previous_status = site.provisioning_status
    if site.provisioning_status == "draft":
        site.provisioning_status = "config_previewed"
    record_audit_event(
        db,
        action="web.site.nginx_preview.generated",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={
            "domain": site.domain,
            "preview_only": "true",
            "saved": "false",
            "previous_provisioning_status": previous_status,
            "provisioning_status": site.provisioning_status,
        },
    )
    db.commit()
    return WebSiteNginxPreviewRead(
        site_id=site.id,
        domain=site.domain,
        config=config,
        saved=False,
    )


@router.get(
    "/web/sites/{site_id}/readiness",
    response_model=WebSiteReadinessRead,
    dependencies=[Depends(require_permission("web.sites.view"))],
)
def get_web_site_readiness(site_id: int, db: Session = Depends(get_db)) -> WebSiteReadinessRead:
    site = _site_or_404(db, site_id)
    return _readiness_read(db, site)


@router.patch(
    "/web/sites/{site_id}/mark-ready",
    response_model=WebSiteRead,
    dependencies=[Depends(require_permission("web.sites.manage"))],
)
def mark_web_site_ready_to_apply(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WebSiteRead:
    site = _site_or_404(db, site_id)
    readiness = _readiness_read(db, site)
    if not readiness.ready:
        failed = [check.label for check in readiness.checks if not check.passed]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Site is not ready to apply: {', '.join(failed)}.",
        )

    previous_status = site.provisioning_status
    site.provisioning_status = "ready_to_apply"
    record_audit_event(
        db,
        action="web.site.ready_to_apply.marked",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={
            "domain": site.domain,
            "previous_provisioning_status": previous_status,
            "provisioning_status": site.provisioning_status,
            "provisioning": "record_only",
        },
    )
    db.commit()
    db.refresh(site)
    return _site_read(site)


@router.get(
    "/web/sites/{site_id}/nginx-apply-plan",
    response_model=WebSiteNginxApplyPlanRead,
    dependencies=[Depends(require_permission("web.sites.view"))],
)
def get_web_site_nginx_apply_plan(
    site_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WebSiteNginxApplyPlanRead:
    site = _site_or_404(db, site_id)
    if site.provisioning_status != "ready_to_apply":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Site must be ready_to_apply before generating an apply plan.",
        )

    plan = _nginx_apply_plan(site, _allowed_base_path(db))
    record_audit_event(
        db,
        action="web.site.nginx_apply_plan.generated",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={
            "domain": site.domain,
            "plan_only": "true",
            "target_config_path": plan.target_config_path,
            "risk_level": plan.risk_level,
        },
    )
    db.commit()
    return plan


@router.get(
    "/web/sites/{site_id}/preflight",
    response_model=WebSitePreflightRead,
    dependencies=[Depends(require_permission("web.sites.view"))],
)
def get_web_site_preflight(site_id: int, db: Session = Depends(get_db)) -> WebSitePreflightRead:
    site = _site_or_404(db, site_id)
    return _web_site_preflight(db, site)


@router.post(
    "/web/sites/{site_id}/nginx-dry-run",
    response_model=WebSiteDryRunRead,
    dependencies=[Depends(require_permission("web.sites.manage"))],
)
def dry_run_web_site_nginx_apply(
    site_id: int,
    payload: WebSiteDryRunRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WebSiteDryRunRead:
    site = _site_or_404(db, site_id)
    if site.provisioning_status != "ready_to_apply":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Site must be ready_to_apply before running a dry-run.",
        )

    allowed_base_path = _allowed_base_path(db)
    plan = _nginx_apply_plan(site, allowed_base_path)
    if payload.confirmation_phrase.strip() != plan.confirmation_phrase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation phrase does not match.",
        )

    record_audit_event(
        db,
        action="web.site.nginx_dry_run.requested",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={
            "domain": site.domain,
            "dry_run": "true",
            "executed": "false",
        },
    )
    result = _nginx_dry_run(site, allowed_base_path)
    record_audit_event(
        db,
        action="web.site.nginx_dry_run.completed",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={
            "domain": site.domain,
            "dry_run": "true",
            "executed": "false",
            "wrote_files": "false",
            "expected_result": result.expected_result,
        },
    )
    db.commit()
    return result


@router.post(
    "/web/sites/{site_id}/nginx-apply",
    response_model=WebSiteApplyRead,
    dependencies=[Depends(require_permission("web.sites.manage"))],
)
def apply_web_site_nginx_config(
    site_id: int,
    payload: WebSiteApplyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WebSiteApplyRead:
    site = _site_or_404(db, site_id)
    if site.provisioning_status != "ready_to_apply":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Site must be ready_to_apply before applying Nginx config.",
        )
    allowed_base_path = _allowed_base_path(db)
    plan = _nginx_apply_plan(site, allowed_base_path)
    if payload.confirmation_phrase.strip() != plan.confirmation_phrase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation phrase does not match.",
        )
    _require_web_site_preflight(db, site, ["web.nginx.apply_site_config"])

    agent_payload = _agent_apply_payload(site, allowed_base_path)
    record_audit_event(
        db,
        action="web.site.nginx_apply.requested",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={"domain": site.domain, "target_config_path": agent_payload["target_config_path"]},
    )
    job, response = execute_mock_agent_action(
        db,
        action="web.nginx.apply_site_config",
        payload=agent_payload,
        user=user,
    )
    site.status = "applied" if response.success else "error"
    site.provisioning_status = "ready_to_apply" if response.success else "error"
    record_audit_event(
        db,
        action="web.site.nginx_apply.completed",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success" if response.success else "failure",
        actor_user_id=user.id,
        metadata={
            "domain": site.domain,
            "job_id": str(job.id),
            "agent_status": response.status,
        },
    )
    db.commit()
    db.refresh(site)
    db.refresh(job)
    return WebSiteApplyRead(
        site=_site_read(site),
        job_id=job.id,
        success=response.success,
        status=response.status,
        result=response.data,
        error=response.error,
    )


@router.post(
    "/web/sites/{site_id}/nginx-disable",
    response_model=WebSiteDisableRead,
    dependencies=[Depends(require_permission("web.sites.manage"))],
)
def disable_web_site_nginx_config(
    site_id: int,
    payload: WebSiteDisableRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WebSiteDisableRead:
    site = _site_or_404(db, site_id)
    if site.status != "applied":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Site must be applied before disabling Nginx config.",
        )

    confirmation_phrase = _nginx_disable_confirmation_phrase(site)
    if payload.confirmation_phrase.strip() != confirmation_phrase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation phrase does not match.",
        )
    _require_web_site_preflight(db, site, ["web.nginx.disable_site_config"])

    agent_payload = _agent_disable_payload(site)
    record_audit_event(
        db,
        action="web.site.nginx_disable.requested",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={"domain": site.domain, "target_config_path": agent_payload["target_config_path"]},
    )
    job, response = execute_mock_agent_action(
        db,
        action="web.nginx.disable_site_config",
        payload=agent_payload,
        user=user,
    )
    site.status = "disabled" if response.success else "error"
    site.provisioning_status = "disabled" if response.success else "error"
    record_audit_event(
        db,
        action="web.site.nginx_disable.completed",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success" if response.success else "failure",
        actor_user_id=user.id,
        metadata={
            "domain": site.domain,
            "job_id": str(job.id),
            "agent_status": response.status,
        },
    )
    db.commit()
    db.refresh(site)
    db.refresh(job)
    return WebSiteDisableRead(
        site=_site_read(site),
        job_id=job.id,
        success=response.success,
        status=response.status,
        result=response.data,
        error=response.error,
    )


@router.post(
    "/web/sites/{site_id}/nginx-reapply",
    response_model=WebSiteReapplyRead,
    dependencies=[Depends(require_permission("web.sites.manage"))],
)
def reapply_web_site_nginx_config(
    site_id: int,
    payload: WebSiteReapplyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> WebSiteReapplyRead:
    site = _site_or_404(db, site_id)
    if site.status not in {"disabled", "error"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Site must be disabled or error before re-applying Nginx config.",
        )

    readiness = _readiness_read(db, site)
    if not readiness.ready:
        failed = [check.label for check in readiness.checks if not check.passed]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Site is not ready to re-apply: {', '.join(failed)}.",
        )

    plan = _nginx_apply_plan(site, _allowed_base_path(db))
    if payload.confirmation_phrase.strip() != plan.confirmation_phrase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation phrase does not match.",
        )
    _require_web_site_preflight(db, site, ["web.nginx.apply_site_config"])

    agent_payload = _agent_apply_payload(site, _allowed_base_path(db))
    record_audit_event(
        db,
        action="web.site.nginx_reapply.requested",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={"domain": site.domain, "target_config_path": agent_payload["target_config_path"]},
    )
    job, response = execute_mock_agent_action(
        db,
        action="web.nginx.apply_site_config",
        payload=agent_payload,
        user=user,
    )
    site.status = "applied" if response.success else "error"
    site.provisioning_status = "ready_to_apply" if response.success else "error"
    record_audit_event(
        db,
        action="web.site.nginx_reapply.completed",
        target_type="web_site",
        target_id=str(site.id),
        outcome="success" if response.success else "failure",
        actor_user_id=user.id,
        metadata={
            "domain": site.domain,
            "job_id": str(job.id),
            "agent_status": response.status,
        },
    )
    db.commit()
    db.refresh(site)
    db.refresh(job)
    return WebSiteReapplyRead(
        site=_site_read(site),
        job_id=job.id,
        success=response.success,
        status=response.status,
        result=response.data,
        error=response.error,
    )


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
        provisioning_status=site.provisioning_status,  # type: ignore[arg-type]
        php_runtime=site.php_runtime,
        ssl_enabled=site.ssl_enabled,
        created_at=site.created_at,
        updated_at=site.updated_at,
    )


def _readiness_read(db: Session, site: WebSite) -> WebSiteReadinessRead:
    checks = _readiness_checks(db, site)
    return WebSiteReadinessRead(
        site_id=site.id,
        domain=site.domain,
        provisioning_status=site.provisioning_status,  # type: ignore[arg-type]
        ready=all(check.passed for check in checks),
        checks=checks,
    )


def _readiness_checks(db: Session, site: WebSite) -> list[WebSiteReadinessCheck]:
    return [
        _check_valid_domain(site),
        _check_safe_root_path(db, site),
        _check_no_duplicate_domain(db, site),
        _check_nginx_preview_available(site),
        _check_ssl_disabled_or_pending(site),
        _check_php_runtime_selected(site),
    ]


def _check_valid_domain(site: WebSite) -> WebSiteReadinessCheck:
    try:
        _validate_domain(site.domain)
        return WebSiteReadinessCheck(
            slug="valid_domain",
            label="Valid domain",
            passed=True,
            detail="Domain format is valid.",
        )
    except HTTPException as exc:
        return WebSiteReadinessCheck(
            slug="valid_domain",
            label="Valid domain",
            passed=False,
            detail=str(exc.detail),
        )


def _check_safe_root_path(db: Session, site: WebSite) -> WebSiteReadinessCheck:
    try:
        _validate_root_path(site.root_path, _allowed_base_path(db))
        return WebSiteReadinessCheck(
            slug="safe_root_path",
            label="Safe root path",
            passed=True,
            detail="Root path is inside the allowed base path.",
        )
    except HTTPException as exc:
        return WebSiteReadinessCheck(
            slug="safe_root_path",
            label="Safe root path",
            passed=False,
            detail=str(exc.detail),
        )


def _check_no_duplicate_domain(db: Session, site: WebSite) -> WebSiteReadinessCheck:
    duplicate = db.scalar(select(WebSite).where(WebSite.domain == site.domain, WebSite.id != site.id))
    return WebSiteReadinessCheck(
        slug="no_duplicate_domain",
        label="No duplicate domain",
        passed=duplicate is None,
        detail="No duplicate site record found." if duplicate is None else "Another site uses this domain.",
    )


def _check_nginx_preview_available(site: WebSite) -> WebSiteReadinessCheck:
    passed = site.provisioning_status in {"config_previewed", "ready_to_apply", "disabled", "error"}
    return WebSiteReadinessCheck(
        slug="nginx_preview_available",
        label="Nginx preview available",
        passed=passed,
        detail="Nginx preview has been generated." if passed else "Generate an Nginx preview first.",
    )


def _check_ssl_disabled_or_pending(site: WebSite) -> WebSiteReadinessCheck:
    return WebSiteReadinessCheck(
        slug="ssl_disabled_pending",
        label="SSL disabled/pending",
        passed=not site.ssl_enabled,
        detail="SSL is disabled or pending." if not site.ssl_enabled else "SSL automation is not available yet.",
    )


def _check_php_runtime_selected(site: WebSite) -> WebSiteReadinessCheck:
    passed = bool(site.php_runtime.strip())
    return WebSiteReadinessCheck(
        slug="php_runtime_selected",
        label="PHP runtime selected",
        passed=passed,
        detail="PHP runtime value is present." if passed else "Select a PHP runtime placeholder.",
    )


def _validate_domain(value: str) -> str:
    domain = value.strip().lower().rstrip(".")
    if not DOMAIN_PATTERN.fullmatch(domain):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Domain must be a valid hostname such as example.com.",
        )
    return domain


def _allowed_base_path(db: Session) -> str:
    setting = db.scalar(select(Setting).where(Setting.key == "web.sites.allowed_base_path"))
    value = setting.value.strip() if setting is not None else DEFAULT_WEB_SITES_BASE_PATH
    return posixpath.normpath(value) if value else DEFAULT_WEB_SITES_BASE_PATH


def _validate_root_path(value: str, allowed_base_path: str) -> str:
    root_path = value.strip()
    if not root_path.startswith("/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Root path must be an absolute path.",
        )
    if "\\" in root_path or "\x00" in root_path:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Root path contains unsupported characters.",
        )
    normalized = posixpath.normpath(root_path)
    if normalized != root_path or ".." in root_path.split("/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Root path must not contain traversal or redundant path segments.",
        )
    if normalized in DANGEROUS_ROOT_PATHS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Root path points to a protected system path.",
        )

    allowed_base = posixpath.normpath(allowed_base_path)
    if normalized != allowed_base and not normalized.startswith(f"{allowed_base}/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Root path must be inside {allowed_base}.",
        )
    return normalized


def _validate_relative_subpath(value: str) -> str:
    raw_subpath = value.strip()
    if not raw_subpath:
        return ""
    if "\\" in raw_subpath or "\x00" in raw_subpath or raw_subpath.startswith("/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Subpath must be a safe relative path.",
        )
    subpath = raw_subpath.strip("/")
    normalized = posixpath.normpath(subpath)
    if normalized != subpath or ".." in normalized.split("/"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Subpath must not contain traversal or redundant path segments.",
        )
    return normalized


def _nginx_preview(site: WebSite) -> str:
    php_target = _php_fpm_target(site.php_runtime)
    return f"""# HostPilot preview only - not written to disk.
# Site status: {site.status}
server {{
    listen 80;
    server_name {site.domain};

    root {site.root_path};
    index index.php index.html;

    access_log /var/log/nginx/hostpilot/{site.domain}.access.log;
    error_log /var/log/nginx/hostpilot/{site.domain}.error.log;

    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}

    location ~ \\.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass {php_target};
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }}
}}
"""


def _nginx_apply_plan(site: WebSite, allowed_webroot_base: str = DEFAULT_WEB_SITES_BASE_PATH) -> WebSiteNginxApplyPlanRead:
    config_filename = f"{site.domain}.conf"
    target_config_path = f"{HOSTPILOT_NGINX_CONFIG_BASE_PATH}/{config_filename}"
    allowed_base = posixpath.normpath(allowed_webroot_base)
    return WebSiteNginxApplyPlanRead(
        site_id=site.id,
        domain=site.domain,
        target_config_path=target_config_path,
        webroot_path=site.root_path,
        required_directories=[
            allowed_base,
            site.root_path,
            "/etc/nginx/sites-available",
            HOSTPILOT_NGINX_CONFIG_BASE_PATH,
            "/etc/nginx/sites-enabled",
            "/var/log/nginx/hostpilot",
        ],
        config_filename=config_filename,
        validation_commands=[
            NGINX_VALIDATION_COMMAND,
            f"test -f {target_config_path}",
            f"test -d {site.root_path}",
        ],
        service_reload_command=NGINX_RELOAD_COMMAND,
        risk_level="medium",
        confirmation_phrase=f"APPLY NGINX PLAN {site.domain}",
        plan_only=True,
    )


def _nginx_dry_run(site: WebSite, allowed_webroot_base: str = DEFAULT_WEB_SITES_BASE_PATH) -> WebSiteDryRunRead:
    plan = _nginx_apply_plan(site, allowed_webroot_base)
    return WebSiteDryRunRead(
        site_id=site.id,
        domain=site.domain,
        config_content=_nginx_preview(site),
        target_config_path=plan.target_config_path,
        webroot_path=plan.webroot_path,
        directory_checks=[f"would ensure directory exists: {directory}" for directory in plan.required_directories],
        nginx_validation_command=plan.validation_commands[0],
        reload_command=plan.service_reload_command,
        expected_result="Dry-run completed. No files, directories, commands, or services were changed.",
        executed=False,
        wrote_files=False,
    )


def _web_site_preflight(
    db: Session,
    site: WebSite,
    required_actions: list[str] | None = None,
) -> WebSitePreflightRead:
    required_agent_actions = required_actions or [
        "web.nginx.apply_site_config",
        "web.nginx.disable_site_config",
    ]
    allowed_web_base_path = _allowed_base_path(db)
    plan = _nginx_apply_plan(site, allowed_web_base_path)
    agent_status = get_agent_status()
    allowed_agent_actions = [str(action) for action in agent_status.get("allowed_actions", [])]
    is_connected = agent_status.get("status") == "connected" and bool(agent_status.get("using_real_agent"))
    target_under_nginx_base = (
        plan.target_config_path == HOSTPILOT_NGINX_CONFIG_BASE_PATH
        or plan.target_config_path.startswith(f"{HOSTPILOT_NGINX_CONFIG_BASE_PATH}/")
    )

    checks = [
        _preflight_check(
            "agent_reachable",
            "Agent reachable",
            is_connected,
            "Local Agent is connected." if is_connected else str(agent_status.get("message", "Local Agent is not connected.")),
        ),
        _preflight_check(
            "agent_real_connected",
            "Agent state is connected",
            agent_status.get("status") == "connected" and not bool(agent_status.get("using_fallback")),
            f"Agent state is {agent_status.get('status')} ({agent_status.get('mode')}).",
        ),
        _preflight_check(
            "required_actions_allowlisted",
            "Required Agent actions allowlisted",
            all(action in allowed_agent_actions for action in required_agent_actions),
            f"Required: {', '.join(required_agent_actions)}.",
        ),
        _preflight_check(
            "allowed_web_base_path",
            "Configured Web allowed base path",
            bool(allowed_web_base_path.startswith("/")),
            f"Webroot base: {allowed_web_base_path}.",
        ),
        _preflight_check(
            "site_root_inside_allowed_base",
            "Site root inside allowed base",
            _path_inside(site.root_path, allowed_web_base_path),
            f"Site root: {site.root_path}.",
        ),
        _preflight_check(
            "nginx_config_base_path",
            "Nginx config base path",
            bool(HOSTPILOT_NGINX_CONFIG_BASE_PATH.startswith("/")),
            f"Nginx config base: {HOSTPILOT_NGINX_CONFIG_BASE_PATH}.",
        ),
        _preflight_check(
            "target_config_inside_nginx_base",
            "Target config under HostPilot Nginx path",
            target_under_nginx_base,
            f"Target config: {plan.target_config_path}.",
        ),
        _preflight_check(
            "nginx_command_declared",
            "Nginx validation command",
            plan.validation_commands[0] == NGINX_VALIDATION_COMMAND,
            f"Command that will run later: {plan.validation_commands[0]}.",
        ),
        _preflight_check(
            "reload_command_declared",
            "Reload command",
            plan.service_reload_command == NGINX_RELOAD_COMMAND,
            f"Command that will run later: {plan.service_reload_command}.",
        ),
        _preflight_check(
            "write_path_assumptions",
            "Write path assumptions",
            _path_inside(site.root_path, allowed_web_base_path) and target_under_nginx_base,
            "Apply is constrained to the configured webroot base and HostPilot Nginx config path.",
        ),
    ]

    return WebSitePreflightRead(
        site_id=site.id,
        domain=site.domain,
        ready=all(check.passed for check in checks),
        agent_status=str(agent_status.get("status", "unavailable")),
        agent_mode=str(agent_status.get("mode", "unknown")),
        using_real_agent=bool(agent_status.get("using_real_agent")),
        using_fallback=bool(agent_status.get("using_fallback")),
        required_agent_actions=required_agent_actions,
        allowed_agent_actions=allowed_agent_actions,
        allowed_web_base_path=allowed_web_base_path,
        nginx_config_base_path=HOSTPILOT_NGINX_CONFIG_BASE_PATH,
        nginx_validation_command=NGINX_VALIDATION_COMMAND,
        reload_command=NGINX_RELOAD_COMMAND,
        checks=checks,
    )


def _require_web_site_preflight(
    db: Session,
    site: WebSite,
    required_actions: list[str],
) -> WebSitePreflightRead:
    preflight = _web_site_preflight(db, site, required_actions)
    if not preflight.ready:
        failed = [check.label for check in preflight.checks if not check.passed]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Web Agent preflight failed: {', '.join(failed)}.",
        )
    return preflight


def _preflight_check(slug: str, label: str, passed: bool, detail: str) -> WebSitePreflightCheck:
    return WebSitePreflightCheck(slug=slug, label=label, passed=passed, detail=detail)


def _path_inside(path: str, base: str) -> bool:
    normalized_path = posixpath.normpath(path)
    normalized_base = posixpath.normpath(base)
    return normalized_path == normalized_base or normalized_path.startswith(f"{normalized_base}/")


def _agent_apply_payload(site: WebSite, allowed_webroot_base: str) -> dict[str, object]:
    plan = _nginx_apply_plan(site, allowed_webroot_base)
    return {
        "domain": site.domain,
        "webroot_path": site.root_path,
        "target_config_path": plan.target_config_path,
        "config_content": _nginx_preview(site),
        "allowed_webroot_base": posixpath.normpath(allowed_webroot_base),
        "allowed_nginx_base": HOSTPILOT_NGINX_CONFIG_BASE_PATH,
    }


def _agent_disable_payload(site: WebSite) -> dict[str, object]:
    plan = _nginx_apply_plan(site)
    return {
        "domain": site.domain,
        "target_config_path": plan.target_config_path,
        "allowed_nginx_base": HOSTPILOT_NGINX_CONFIG_BASE_PATH,
    }


def _agent_logs_payload(site: WebSite, lines: int) -> dict[str, object]:
    return {
        "domain": site.domain,
        "line_limit": min(lines, MAX_WEB_LOG_LINES),
        "allowed_log_base": DEFAULT_WEB_LOG_BASE_PATH,
    }


def _agent_files_payload(
    site: WebSite,
    relative_subpath: str,
    page: int,
    page_size: int,
    allowed_webroot_base: str,
) -> dict[str, object]:
    return {
        "root_path": site.root_path,
        "relative_subpath": relative_subpath,
        "page": page,
        "page_size": min(page_size, MAX_WEB_FILE_PAGE_SIZE),
        "allowed_webroot_base": posixpath.normpath(allowed_webroot_base),
    }


def _log_file_read(payload: object) -> WebSiteLogFileRead:
    if not isinstance(payload, dict):
        return WebSiteLogFileRead(path="", missing=True, lines=[])
    lines = payload.get("lines", [])
    return WebSiteLogFileRead(
        path=str(payload.get("path", "")),
        missing=bool(payload.get("missing", True)),
        lines=[str(line) for line in lines] if isinstance(lines, list) else [],
    )


def _file_entries_read(payload: object) -> list[WebSiteFileEntryRead]:
    if not isinstance(payload, list):
        return []
    entries: list[WebSiteFileEntryRead] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        entry_type = "directory" if entry.get("type") == "directory" else "file"
        entries.append(
            WebSiteFileEntryRead(
                name=str(entry.get("name", "")),
                type=entry_type,  # type: ignore[arg-type]
                size=int(entry.get("size", 0)),
                modified_at=float(entry.get("modified_at", 0)),
                relative_path=str(entry.get("relative_path", "")),
            )
        )
    return entries


def _nginx_disable_confirmation_phrase(site: WebSite) -> str:
    return f"DISABLE NGINX SITE {site.domain}"


def _php_fpm_target(php_runtime: str) -> str:
    normalized = php_runtime.strip().lower()
    if normalized in {"", "none"}:
        return "unix:/run/php/hostpilot-placeholder.sock"
    if normalized.startswith("unix:") or normalized.startswith("127.0.0.1:"):
        return normalized
    version = normalized.removeprefix("php-").removeprefix("php")
    return f"unix:/run/php/php{version}-fpm.sock"
