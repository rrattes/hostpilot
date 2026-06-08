from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.orm import Session

from app.db.models import CoreBackup, User


BACKUP_DIR_ENV = "HOSTPILOT_BACKUP_DIR"
CORE_CONFIG_FILES = ("alembic.ini", "pyproject.toml", "requirements.txt")


def get_backup_dir() -> Path:
    configured = os.getenv(BACKUP_DIR_ENV)
    return Path(configured).expanduser().resolve() if configured else (Path.cwd() / ".dev" / "backups").resolve()


def create_core_backup(db: Session, user: User) -> tuple[CoreBackup, list[str]]:
    backup_id = str(uuid4())
    backup_dir = get_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"hostpilot-core-{backup_id}.zip"

    backup = CoreBackup(
        id=backup_id,
        created_by=user.id,
        status="running",
        file_path=str(backup_path),
        size_bytes=0,
    )
    db.add(backup)
    db.flush()

    try:
        included_files = _write_backup_archive(db, backup_path, backup_id, user)
        backup.status = "completed"
        backup.size_bytes = backup_path.stat().st_size
        backup.file_path = str(backup_path)
        db.flush()
    except Exception:
        backup.status = "failed"
        backup.size_bytes = backup_path.stat().st_size if backup_path.exists() else 0
        backup.file_path = str(backup_path)
        db.flush()
        raise

    return backup, included_files


def _write_backup_archive(
    db: Session,
    backup_path: Path,
    backup_id: str,
    user: User,
) -> list[str]:
    backend_root = Path.cwd().resolve()
    included_files: list[str] = []
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        sqlite_backup_path = temp_path / "hostpilot.db"
        sqlite_source = _sqlite_database_path(db, backend_root)

        with ZipFile(backup_path, "w", compression=ZIP_DEFLATED) as archive:
            if sqlite_source is not None and sqlite_source.exists():
                _copy_sqlite_database(sqlite_source, sqlite_backup_path)
                archive.write(sqlite_backup_path, "database/hostpilot.db")
                included_files.append("database/hostpilot.db")

            for file_name in CORE_CONFIG_FILES:
                config_path = backend_root / file_name
                if config_path.exists() and config_path.is_file():
                    archive.write(config_path, f"core-config/{file_name}")
                    included_files.append(f"core-config/{file_name}")

            manifest = {
                "id": backup_id,
                "created_at": datetime.now(UTC).isoformat(),
                "created_by": user.email,
                "sqlite_database_included": "database/hostpilot.db" in included_files,
                "included_files": included_files,
                "notes": "Core backup excludes websites, Nginx configs, SSL certs, and secrets.",
            }
            archive.writestr("manifest.json", json.dumps(manifest, indent=2))
            included_files.append("manifest.json")

    return included_files


def _sqlite_database_path(db: Session, backend_root: Path) -> Path | None:
    bind = db.get_bind()
    database = getattr(bind.url, "database", None)
    drivername = getattr(bind.url, "drivername", "")
    if not drivername.startswith("sqlite") or not database or database == ":memory:":
        return None

    database_path = Path(database)
    if not database_path.is_absolute():
        database_path = backend_root / database_path
    return database_path.resolve()


def _copy_sqlite_database(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_connection = sqlite3.connect(source)
    try:
        destination_connection = sqlite3.connect(destination)
        try:
            source_connection.backup(destination_connection)
        finally:
            destination_connection.close()
    finally:
        source_connection.close()
