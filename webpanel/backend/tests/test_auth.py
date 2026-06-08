from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth.rate_limit import clear_all_login_attempts
from app.core.auth.security import (
    create_access_token,
    get_secret_key,
    hash_password,
    validate_password_policy,
    verify_password,
)
from app.db.base import Base
from app.db.models import AuditEvent, User
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
    clear_all_login_attempts()
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db


def teardown_function() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    clear_all_login_attempts()


def test_password_hashing_uses_argon2id() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash != "correct horse battery staple"
    assert password_hash.startswith("$argon2id$")
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_password_policy_requires_minimum_complexity() -> None:
    assert validate_password_policy("StrongPassword123!") == []

    errors = validate_password_policy("short")

    assert "Password must be at least 12 characters." in errors
    assert "Password must include an uppercase letter." in errors
    assert "Password must include a number." in errors
    assert "Password must include a symbol." in errors


def test_secret_key_required_outside_dev_and_test(monkeypatch) -> None:
    monkeypatch.delenv("HOSTPILOT_SECRET_KEY", raising=False)
    monkeypatch.setenv("HOSTPILOT_ENV", "production")

    try:
        get_secret_key()
    except RuntimeError as exc:
        assert "HOSTPILOT_SECRET_KEY is required" in str(exc)
    else:
        raise AssertionError("Expected HOSTPILOT_SECRET_KEY to be required in production.")


def test_secret_key_dev_fallback_is_explicit(monkeypatch) -> None:
    monkeypatch.delenv("HOSTPILOT_SECRET_KEY", raising=False)
    monkeypatch.setenv("HOSTPILOT_ENV", "test")

    assert get_secret_key() == "dev-only-change-me"


def test_login_and_current_user() -> None:
    with TestingSessionLocal() as db:
        db.add(
            User(
                email="admin@example.com",
                display_name="Admin",
                password_hash=hash_password("correct horse battery staple"),
                is_active=True,
                is_superuser=True,
            )
        )
        db.commit()

    client = TestClient(app)
    login_response = client.post(
        "/api/core/auth/login",
        json={"email": "admin@example.com", "password": "correct horse battery staple"},
    )

    assert login_response.status_code == 200
    login_payload = login_response.json()
    token = login_payload["access_token"]
    assert login_payload["expires_in_minutes"] == 60

    me_response = client.get(
        "/api/core/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "admin@example.com"
    assert me_response.json()["is_superuser"] is True

    with TestingSessionLocal() as db:
        audit_event = db.scalar(select(AuditEvent).where(AuditEvent.action == "auth.login.succeeded"))

    assert audit_event is not None
    assert audit_event.outcome == "success"


def test_login_uses_configurable_token_lifetime(monkeypatch) -> None:
    monkeypatch.setenv("HOSTPILOT_ACCESS_TOKEN_MINUTES", "15")
    with TestingSessionLocal() as db:
        db.add(
            User(
                email="admin@example.com",
                display_name="Admin",
                password_hash=hash_password("correct horse battery staple"),
                is_active=True,
                is_superuser=True,
            )
        )
        db.commit()

    client = TestClient(app)
    response = client.post(
        "/api/core/auth/login",
        json={"email": "admin@example.com", "password": "correct horse battery staple"},
    )

    assert response.status_code == 200
    assert response.json()["expires_in_minutes"] == 15


def test_failed_login_writes_audit_event() -> None:
    with TestingSessionLocal() as db:
        db.add(
            User(
                email="admin@example.com",
                display_name="Admin",
                password_hash=hash_password("correct horse battery staple"),
                is_active=True,
                is_superuser=True,
            )
        )
        db.commit()

    client = TestClient(app)
    response = client.post(
        "/api/core/auth/login",
        json={"email": "admin@example.com", "password": "wrong password"},
    )

    assert response.status_code == 401

    with TestingSessionLocal() as db:
        audit_event = db.scalar(select(AuditEvent).where(AuditEvent.action == "auth.login.failed"))

    assert audit_event is not None
    assert audit_event.outcome == "failure"


def test_current_user_can_change_password() -> None:
    with TestingSessionLocal() as db:
        user = User(
            email="admin@example.com",
            display_name="Admin",
            password_hash=hash_password("CurrentPassword123!"),
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
        token = create_access_token(user.id)

    client = TestClient(app)
    response = client.post(
        "/api/core/auth/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "CurrentPassword123!", "new_password": "NextPassword123!"},
    )

    assert response.status_code == 200

    with TestingSessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "admin@example.com"))
        audit_event = db.scalar(
            select(AuditEvent).where(AuditEvent.action == "auth.password_change.succeeded")
        )

    assert user is not None
    assert verify_password("NextPassword123!", user.password_hash)
    assert audit_event is not None
    assert audit_event.outcome == "success"


def test_password_change_rejects_wrong_current_password_and_audits_failure() -> None:
    with TestingSessionLocal() as db:
        user = User(
            email="admin@example.com",
            display_name="Admin",
            password_hash=hash_password("CurrentPassword123!"),
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
        token = create_access_token(user.id)

    client = TestClient(app)
    response = client.post(
        "/api/core/auth/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "WrongPassword123!", "new_password": "NextPassword123!"},
    )

    assert response.status_code == 400

    with TestingSessionLocal() as db:
        audit_event = db.scalar(
            select(AuditEvent).where(AuditEvent.action == "auth.password_change.failed")
        )

    assert audit_event is not None
    assert audit_event.outcome == "failure"


def test_password_change_rejects_weak_password_and_audits_failure() -> None:
    with TestingSessionLocal() as db:
        user = User(
            email="admin@example.com",
            display_name="Admin",
            password_hash=hash_password("CurrentPassword123!"),
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
        token = create_access_token(user.id)

    client = TestClient(app)
    response = client.post(
        "/api/core/auth/password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": "CurrentPassword123!", "new_password": "weak"},
    )

    assert response.status_code == 400
    assert "Password must be at least 12 characters." in response.json()["detail"]

    with TestingSessionLocal() as db:
        audit_event = db.scalar(
            select(AuditEvent).where(AuditEvent.action == "auth.password_change.failed")
        )

    assert audit_event is not None
    assert audit_event.outcome == "failure"


def test_logout_documents_stateless_bearer_behavior_and_audits() -> None:
    with TestingSessionLocal() as db:
        user = User(
            email="admin@example.com",
            display_name="Admin",
            password_hash=hash_password("CurrentPassword123!"),
            is_active=True,
            is_superuser=True,
        )
        db.add(user)
        db.commit()
        token = create_access_token(user.id)

    client = TestClient(app)
    response = client.post(
        "/api/core/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert "discard the token client-side" in response.json()["message"]

    with TestingSessionLocal() as db:
        audit_event = db.scalar(select(AuditEvent).where(AuditEvent.action == "auth.logout.requested"))

    assert audit_event is not None
    assert audit_event.outcome == "success"
