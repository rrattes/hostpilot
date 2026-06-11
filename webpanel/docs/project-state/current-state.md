# HostPilot Current Project State

Date: 2026-06-11

## Repository

- Canonical local repository root: `C:\Users\Admin\OneDrive\Documentos\WebManager`.
- Project root inside the repository: `webpanel/`.
- Current branch: `main`.
- Git remote: `https://github.com/rrattes/hostpilot.git`.
- Current local branch status: ahead of `origin/main` with Core implementation commits and behind `origin/main` with remote-only commits. Remote reconciliation is still required before a normal fast-forward push can succeed.

## Current Repo Structure

```text
webpanel/
  backend/
    alembic/
    app/
      api/
      core/
      db/
      scripts/
      services/
    tests/
  frontend/
    src/
      components/
      pages/
      services/
  agent/
    tests/
    webpanel_agent/
      actions/
      mock/
      policies/
  deploy/
    nginx/
    scripts/
    systemd/
  docs/
    architecture/
    deploy/
    modules/
    project-state/
    security/
  scripts/
    dev.ps1
    test.ps1
```

## Latest Implemented Core Items

- Backend Core API is implemented with FastAPI, SQLite, SQLAlchemy, Alembic migrations, RBAC dependencies, audit log, jobs, notifications, module registry, settings/server record, auth/session basics, user management, roles/permissions read APIs, local Agent gateway, and Core backup endpoints.
- Auth/session basics include mandatory `HOSTPILOT_SECRET_KEY` outside dev/test, explicit dev/test fallback, configurable token lifetime, minimum password policy, current-user password change endpoint, and documented stateless logout behavior.
- User management supports listing users, creating users, active status updates, role assignment, manual password reset, and audit events for the relevant mutations.
- Roles & Permissions UI is read-only and shows seeded Core roles, assigned permissions, and users where available.
- Core Backup is implemented as a manual create/list flow with RBAC permissions, persisted metadata, audit events, configurable dev-safe backup path, SQLite/config manifest archive content, and backend regression coverage.
- Agent transport is implemented as a local HTTP service bound to loopback with allowlisted `mock.health` and `mock.system_info`, request/response validation, timeout handling, request IDs, and backend fallback to mock when unavailable in development.
- Frontend includes Login, Dashboard, Agent, Audit Log, Jobs, Notifications, Server, Settings, Users, Roles & Permissions, Backups, and Change Password views with the dark technical console style.
- Windows development scripts exist for local dev/test workflows under `webpanel/scripts/`.
- GitHub Actions CI exists at `.github/workflows/ci.yml` in the tracked history and validates backend, agent, and frontend jobs with Python 3.13 alignment.
- Ubuntu lab deployment templates, installer, and check scripts exist under `webpanel/deploy/`, with the lab runtime pinned to isolated Python 3.13 under `/opt/hostpilot/python`.

## Latest Validation Results

Latest full validation recorded during Core readiness:

| Check | Result |
| --- | --- |
| Backend pytest | Pass: `48 passed`. |
| Agent pytest | Pass: `6 passed`. |
| Frontend tests | Not configured: no frontend `test` script exists. |
| Frontend build | Pass: production build completed. |

Current documentation update validation from the local workspace:

| Check | Result |
| --- | --- |
| Backend pytest | Pass: `48 passed` using the available Codex Python runtime plus backend venv site-packages and workspace-local `TEMP/TMP`. |
| Agent pytest | Not valid locally: collected `0` tests because tracked agent test/package files are currently missing from the working tree. |
| Frontend tests | No-op: no frontend `test` script is configured. |
| Frontend build | Pass: production build completed. |

The working tree currently has missing tracked files, including `.github/workflows/ci.yml`, `webpanel/.gitignore`, `webpanel/README.md`, and some agent packaging/test files. Those deletions are not included in this documentation update and should be reconciled before publishing destructive changes.

## CI Status

- GitHub Actions workflow is defined for push and pull request validation against `main`.
- Jobs cover backend migrations/tests, agent tests, and frontend build.
- Latest remote CI result was not queried in this local documentation pass.

## Ubuntu Lab Status

- Ubuntu lab deployment was validated on Ubuntu 26.04 at `192.168.0.63` using lab-only root SSH.
- Core was bound to `127.0.0.1:8000`.
- Agent was bound to `127.0.0.1:8765`.
- Nginx exposed the lab UI on port `8080`.
- Python runtime decision: use isolated Python 3.13 under `/opt/hostpilot/python`; do not rely on Ubuntu 26.04 system Python 3.14 for app runtime yet.
- Remaining lab task: re-run `install-lab.sh` and `check-lab.sh` end-to-end after the Python 3.13 pin.

## Security Gate Status

- Core Security Gate document exists at `webpanel/docs/security/core-security-gate.md`.
- Security Gate results are recorded in `webpanel/docs/project-state/security-gate-results-2026-06-08.md`.
- Practical checks passed: backend tests, agent tests, frontend build, frontend audit, local file ignore review, and basic Agent allowlist review.
- Pending checks: Python dependency scan, Python security linting, OWASP ZAP baseline, Nessus/OpenVAS readiness, and formal RBAC/IDOR/BOLA manual matrix.

## Audit Coverage Status

- Audit coverage matrix exists at `webpanel/docs/project-state/audit-coverage-matrix.md`.
- Implemented Core mutation workflows are covered or partially covered according to the matrix.
- Known audit hardening gaps remain: retention enforcement, export policy, tamper-resistant storage decision, and formal read-access audit policy.

## Frontend Regression Test Status

- Frontend production build passes in the latest recorded validation.
- No automated frontend test script is configured yet.
- Recommended next frontend quality step is to add focused regression coverage for authenticated shell routing, Dashboard rendering, Settings account actions, Users, Roles, and Backups.

## Known Gaps

- Local Git worktree currently shows missing tracked files and untracked `webpanel/.git.backup/` contents. This must be cleaned or intentionally reconciled before pushing a clean state.
- Local `main` is ahead of and behind `origin/main`; normal push may be rejected until remote-only commits are integrated.
- Core is ready to start Web module work only with known gaps; it is not production/release ready.
- No refresh tokens, token revocation store, password reset email, SSO/OAuth, or 2FA yet.
- No restore, scheduled backup, cloud backup, website backup, Nginx backup, or SSL backup.
- Jobs remain simple/synchronous for Core flows; no worker queue, retries, or scheduler.
- Security Gate remains partial until the external/manual checks are completed.

## Current Development Ports

- Backend: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Frontend: `http://127.0.0.1:5173`
- Agent: `http://127.0.0.1:8765`
- Ubuntu lab UI through Nginx: `http://192.168.0.63:8080`

## Core Readiness Decision

Current decision: Ready with Known Gaps for starting the Web module.

This means Web module work can begin behind the existing Core module/RBAC/audit/Agent boundaries. It does not mean Core is ready for production release.

## Next Recommended Technical Step

Reconcile local `main` with `origin/main` and clean the missing tracked files before pushing. After Git state is clean, add focused frontend regression tests for the authenticated Core shell and Core admin pages.
