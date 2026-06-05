from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth.rate_limit import clear_all_login_attempts
from app.core.auth.security import hash_password, verify_password
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
    token = login_response.json()["access_token"]

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
