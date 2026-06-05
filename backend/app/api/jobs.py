from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit.events import record_audit_event
from app.core.auth.dependencies import get_current_user
from app.core.rbac.permissions import require_permission
from app.db.models import Job, User
from app.db.session import get_db


router = APIRouter()


class JobRead(BaseModel):
    id: int
    type: str
    module: str
    action: str
    status: str
    payload: str
    result: str | None
    created_at: datetime
    updated_at: datetime


class JobList(BaseModel):
    items: list[JobRead]
    total: int
    limit: int
    offset: int


class MockJobCreate(BaseModel):
    module: str = "core"
    action: str = "mock.dev"
    payload: str = "{}"


def _job_read(job: Job) -> JobRead:
    return JobRead(
        id=job.id,
        type=job.type,
        module=job.module,
        action=job.action,
        status=job.status,
        payload=job.payload,
        result=job.result,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


@router.get("/jobs", response_model=JobList, dependencies=[Depends(require_permission("jobs.view"))])
def list_jobs(
    db: Session = Depends(get_db),
    status: str | None = None,
    module: str | None = None,
    action: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> JobList:
    statement = select(Job)

    if status:
        statement = statement.where(Job.status == status)
    if module:
        statement = statement.where(Job.module == module)
    if action:
        statement = statement.where(Job.action == action)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    jobs = db.scalars(statement.order_by(Job.created_at.desc()).limit(limit).offset(offset)).all()

    return JobList(items=[_job_read(job) for job in jobs], total=total, limit=limit, offset=offset)


@router.get("/jobs/{job_id}", response_model=JobRead, dependencies=[Depends(require_permission("jobs.view"))])
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobRead:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _job_read(job)


@router.post("/jobs/mock", response_model=JobRead, dependencies=[Depends(require_permission("jobs.view"))])
def create_mock_job(
    payload: MockJobCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> JobRead:
    job = Job(
        type="mock",
        module=payload.module,
        action=payload.action,
        status="queued",
        payload=payload.payload,
    )
    db.add(job)
    db.flush()
    record_audit_event(
        db,
        action="jobs.mock.created",
        target_type="job",
        target_id=str(job.id),
        outcome="success",
        actor_user_id=user.id,
        metadata={"module": job.module, "job_action": job.action},
    )
    db.commit()
    db.refresh(job)
    return _job_read(job)
