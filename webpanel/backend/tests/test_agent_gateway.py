from collections.abc import Generator
import json
import logging

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.agent_gateway.contracts import AgentActionRequest, AgentActionResponse
from app.core.agent_gateway.local_client import LocalAgentTransportError
from app.core.auth.security import create_access_token
from app.db.base import Base
from app.db.models import AuditEvent, Job, Permission, Role, User
from app.db.session import get_db
from app.main import app


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_function() -> None:
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db


def teardown_function() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _token(email: str, permission_slugs: list[str]) -> str:
    with TestingSessionLocal() as db:
        permissions = [Permission(slug=slug, description="") for slug in permission_slugs]
        role = Role(slug=email.split("@")[0], name="Test Role", permissions=permissions)
        user = User(email=email, display_name="Test User", password_hash="not-used", roles=[role])
        db.add(user)
        db.commit()
        return create_access_token(user.id)


def test_unknown_action_rejected_and_job_failed() -> None:
    token = _token("operator@example.com", ["agent.execute_mock"])
    client = TestClient(app)

    response = client.post(
        "/api/agent/actions/real.system",
        headers={"Authorization": f"Bearer {token}"},
        json={"payload": {}},
    )

    assert response.status_code == 400
    with TestingSessionLocal() as db:
        job = db.scalar(select(Job).where(Job.module == "agent"))
        audit_event = db.scalar(
            select(AuditEvent).where(AuditEvent.action == "agent.action.completed")
        )

    assert job is not None
    assert job.status == "failed"
    assert audit_event is not None
    assert audit_event.outcome == "failure"


def test_viewer_cannot_execute_mock_action() -> None:
    token = _token("viewer@example.com", ["agent.view"])
    client = TestClient(app)

    response = client.post(
        "/api/agent/actions/mock.health",
        headers={"Authorization": f"Bearer {token}"},
        json={"payload": {}},
    )

    assert response.status_code == 403


def test_operator_can_execute_mock_action() -> None:
    token = _token("operator@example.com", ["agent.execute_mock"])
    client = TestClient(app)

    response = client.post(
        "/api/agent/actions/mock.health",
        headers={"Authorization": f"Bearer {token}"},
        json={"payload": {}},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["status"] == "ok"


def test_operator_action_uses_local_agent_transport(monkeypatch) -> None:
    captured_request: AgentActionRequest | None = None

    def fake_execute_local_agent_action(request: AgentActionRequest) -> AgentActionResponse:
        nonlocal captured_request
        captured_request = request
        return AgentActionResponse(
            success=True,
            status="completed",
            data={"status": "ok", "mode": "local-http"},
            error=None,
            duration_ms=5,
        )

    monkeypatch.setattr(
        "app.core.agent_gateway.service.execute_local_agent_action",
        fake_execute_local_agent_action,
    )
    token = _token("operator@example.com", ["agent.execute_mock"])
    client = TestClient(app)

    response = client.post(
        "/api/agent/actions/mock.health",
        headers={"Authorization": f"Bearer {token}"},
        json={"payload": {}},
    )

    assert response.status_code == 200
    assert response.json()["data"]["mode"] == "local-http"
    assert captured_request is not None
    assert captured_request.action == "mock.health"
    assert captured_request.requested_by == "operator@example.com"
    assert captured_request.request_id


def test_dev_fallback_to_mock_logged_when_local_agent_unavailable(caplog, monkeypatch) -> None:
    def raise_transport_error(request: AgentActionRequest) -> AgentActionResponse:
        raise LocalAgentTransportError("offline")

    monkeypatch.setattr(
        "app.core.agent_gateway.service.execute_local_agent_action",
        raise_transport_error,
    )
    caplog.set_level(logging.WARNING, logger="app.core.agent_gateway.service")
    token = _token("operator@example.com", ["agent.execute_mock"])
    client = TestClient(app)

    response = client.post(
        "/api/agent/actions/mock.health",
        headers={"Authorization": f"Bearer {token}"},
        json={"payload": {}},
    )

    assert response.status_code == 200
    assert response.json()["data"]["mode"] == "mock"
    assert "using dev mock fallback" in caplog.text


def test_job_created_and_completed_with_result() -> None:
    token = _token("operator@example.com", ["agent.execute_mock"])
    client = TestClient(app)

    response = client.post(
        "/api/agent/actions/mock.system_info",
        headers={"Authorization": f"Bearer {token}"},
        json={"payload": {}},
    )

    assert response.status_code == 200
    with TestingSessionLocal() as db:
        job = db.get(Job, response.json()["job_id"])

    assert job is not None
    assert job.status == "completed"
    assert job.action == "mock.system_info"
    assert job.result is not None
    assert json.loads(job.result)["data"]["hostname"] == "hostpilot-local-dev"


def test_audit_event_created_for_agent_action() -> None:
    token = _token("operator@example.com", ["agent.execute_mock"])
    client = TestClient(app)

    response = client.post(
        "/api/agent/actions/mock.health",
        headers={"Authorization": f"Bearer {token}"},
        json={"payload": {}},
    )

    assert response.status_code == 200
    with TestingSessionLocal() as db:
        requested = db.scalar(select(AuditEvent).where(AuditEvent.action == "agent.action.requested"))
        completed = db.scalar(select(AuditEvent).where(AuditEvent.action == "agent.action.completed"))

    assert requested is not None
    assert completed is not None
    assert completed.outcome == "success"
