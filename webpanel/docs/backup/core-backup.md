# HostPilot Core Backup

Core backup is a local, manual safeguard for development and lab use.

## What Is Included

- SQLite Core database when the active SQLAlchemy database URL points to a
  local SQLite file.
- Core backend config/state files that exist:
  - `alembic.ini`
  - `pyproject.toml`
  - `requirements.txt`
- A `manifest.json` file describing the backup contents.

## Storage

Backups are written to `HOSTPILOT_BACKUP_DIR` when set. If unset, the backend
uses `.dev/backups` under its current working directory.

Each backup creates metadata with:

- `id`
- `created_at`
- `created_by`
- `status`
- `file_path`
- `size_bytes`

## API

- `POST /api/core/backups`
  - Requires `core.backup.create`.
  - Creates a Core backup archive.
- `GET /api/core/backups`
  - Requires `core.backup.view`.
  - Lists backup metadata.

## Exclusions

- No websites.
- No Nginx configs.
- No SSL certificates.
- No `/etc/hostpilot` secrets.
- No scheduled backups.
- No cloud backup.
- No destructive restore automation.
