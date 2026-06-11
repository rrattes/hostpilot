from datetime import datetime
import posixpath
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.agent_gateway.service import execute_mock_agent_action
from app.core.audit.events import record_audit_event
from app.core.auth.dependencies import get_current_user
from app.core.rbac.permissions import require_permission
from app.db.models import Module, Setting, User, WebSite
from app.db.session import get_db


router = APIRouter()


SectionStatus = Literal["unavailable", "coming_soon"]
ProvisioningStatus = Literal["draft", "config_previewed", "ready_to_apply", "disabled", "error"]
DEFAULT_WEB_SITES_BASE_PATH = "/var/www/hostpilot-sites"
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

    plan = _nginx_apply_plan(site)
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

    plan = _nginx_apply_plan(site)
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
    result = _nginx_dry_run(site)
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
    plan = _nginx_apply_plan(site)
    if payload.confirmation_phrase.strip() != plan.confirmation_phrase:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation phrase does not match.",
        )

    agent_payload = _agent_apply_payload(site)
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
    passed = site.provisioning_status in {"config_previewed", "ready_to_apply"}
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


def _nginx_apply_plan(site: WebSite) -> WebSiteNginxApplyPlanRead:
    config_filename = f"{site.domain}.conf"
    target_config_path = f"/etc/nginx/sites-available/hostpilot/{config_filename}"
    return WebSiteNginxApplyPlanRead(
        site_id=site.id,
        domain=site.domain,
        target_config_path=target_config_path,
        webroot_path=site.root_path,
        required_directories=[
            site.root_path,
            "/etc/nginx/sites-available",
            "/etc/nginx/sites-available/hostpilot",
            "/etc/nginx/sites-enabled",
            "/var/log/nginx/hostpilot",
        ],
        config_filename=config_filename,
        validation_commands=[
            "nginx -t",
            f"test -f {target_config_path}",
            f"test -d {site.root_path}",
        ],
        service_reload_command="systemctl reload nginx",
        risk_level="medium",
        confirmation_phrase=f"APPLY NGINX PLAN {site.domain}",
        plan_only=True,
    )


def _nginx_dry_run(site: WebSite) -> WebSiteDryRunRead:
    plan = _nginx_apply_plan(site)
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


def _agent_apply_payload(site: WebSite) -> dict[str, object]:
    plan = _nginx_apply_plan(site)
    return {
        "domain": site.domain,
        "webroot_path": site.root_path,
        "target_config_path": plan.target_config_path,
        "config_content": _nginx_preview(site),
        "allowed_webroot_base": DEFAULT_WEB_SITES_BASE_PATH,
        "allowed_nginx_base": "/etc/nginx/sites-available/hostpilot",
    }


def _agent_disable_payload(site: WebSite) -> dict[str, object]:
    plan = _nginx_apply_plan(site)
    return {
        "domain": site.domain,
        "target_config_path": plan.target_config_path,
        "allowed_nginx_base": "/etc/nginx/sites-available/hostpilot",
    }


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
