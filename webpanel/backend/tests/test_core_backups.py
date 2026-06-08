from collections.abc import Generator
import json
from pathlib import Path
from zipfile import ZipFile

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.auth.security import create_access_token
from app.db.base import Base
from app.db.models import AuditEvent, CoreBackup, Permission, Role, User
from app.db.session import get_db
from app.main import app


def _client_for_database(database_path: Path) -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine(
        f"sqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), testing_session_local


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _seed_user(
    testing_session_local: sessionmaker[Session],
    email: str,
    permission_slugs: list[str],
) -> str:
    with testing_session_local() as db:
        permissions = [Permission(slug=slug, description=slug) for slug in permission_slugs]
        role = Role(slug=email.split("@")[0], name="Backup Role", permissions=permissions)
        user = User(email=email, display_name="Backup User", password_hash="not-used", roles=[role])
        db.add(user)
        db.commit()
        return create_access_token(user.id)


def test_admin_can_create_and_list_core_backups(tmp_path, monkeypatch) -> None:
    database_path = tmp_path / "hostpilot.db"
    backup_dir = tmp_path / "backups"
    monkeypatch.setenv("HOSTPILOT_BACKUP_DIR", str(backup_dir))
    client, testing_session_local = _client_for_database(database_path)
    try:
        token = _seed_user(
            testing_session_local,
            "admin@example.com",
            ["core.backup.create", "core.backup.view"],
        )

        create_response = client.post(
            "/api/core/backups",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert create_response.status_code == 200
        backup_payload = create_response.json()
        assert backup_payload["status"] == "completed"
        assert backup_payload["created_by"] is not None
        assert backup_payload["size_bytes"] > 0
        backup_path = Path(backup_payload["file_path"])
        assert backup_path.exists()
        assert backup_path.parent == backup_dir

        with ZipFile(backup_path) as archive:
            names = set(archive.namelist())
            manifest = json.loads(archive.read("manifest.json"))

        assert "database/hostpilot.db" in names
        assert "core-config/alembic.ini" in names
        assert manifest["sqlite_database_included"] is True

        list_response = client.get(
            "/api/core/backups",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert list_response.status_code == 200
        assert list_response.json()[0]["id"] == backup_payload["id"]

        with testing_session_local() as db:
            backup = db.get(CoreBackup, backup_payload["id"])
            audit_event = db.scalar(
                select(AuditEvent).where(AuditEvent.action == "core.backup.created")
            )

        assert backup is not None
        assert backup.status == "completed"
        assert audit_event is not None
        assert audit_event.outcome == "success"
    finally:
        _clear_overrides()


def test_backup_endpoints_require_permissions(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("HOSTPILOT_BACKUP_DIR", str(tmp_path / "backups"))
    client, testing_session_local = _client_for_database(tmp_path / "hostpilot.db")
    try:
        token = _seed_user(testing_session_local, "viewer@example.com", [])

        create_response = client.post(
            "/api/core/backups",
            headers={"Authorization": f"Bearer {token}"},
        )
        list_response = client.get(
            "/api/core/backups",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert create_response.status_code == 403
        assert list_response.status_code == 403
    finally:
        _clear_overrides()


def test_backup_failure_is_audited(tmp_path, monkeypatch) -> None:
    blocking_file = tmp_path / "not-a-directory"
    blocking_file.write_text("blocked")
    monkeypatch.setenv("HOSTPILOT_BACKUP_DIR", str(blocking_file))
    client, testing_session_local = _client_for_database(tmp_path / "hostpilot.db")
    try:
        token = _seed_user(
            testing_session_local,
            "admin@example.com",
            ["core.backup.create"],
        )

        response = client.post(
            "/api/core/backups",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 500
        with testing_session_local() as db:
            audit_event = db.scalar(
                select(AuditEvent).where(AuditEvent.action == "core.backup.failed")
            )

        assert audit_event is not None
        assert audit_event.outcome == "failure"
    finally:
        _clear_overrides()
