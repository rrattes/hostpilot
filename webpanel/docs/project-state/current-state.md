# HostPilot Current Project State

Date: 2026-06-05

## 1. Current Repository Structure

```text
webpanel/
  backend/
    alembic/
      versions/
    app/
      api/
      core/
      db/
      scripts/
      main.py
    tests/
    alembic.ini
    pyproject.toml
    requirements.txt
  frontend/
    src/
      components/
      core/
      pages/
    index.html
    package.json
    tsconfig.json
    vite.config.ts
  agent/
    webpanel_agent/
      actions/
      mock/
      policies/
      contracts.py
      main.py
    tests/
    pyproject.toml
    requirements.txt
  deploy/
  docs/
    architecture/
    modules/
    project-state/
    security/
```

The repository is still rooted under the `webpanel/` folder and uses package names such as `webpanel-agent` and `webpanel-frontend`. The product-facing name is HostPilot.

## 2. Implemented So Far

- Monorepo scaffold for backend, frontend, agent, deploy placeholders, and docs.
- FastAPI backend with SQLite, SQLAlchemy models, Alembic migrations, and tests.
- JWT login flow with Argon2id password hashing and admin bootstrap script.
- Backend-enforced RBAC with seeded roles and permissions.
- Module registry with safe state management only.
- Settings, local server display record, audit log, jobs, notifications, health/status, and mock agent gateway endpoints.
- React/Vite frontend with dark technical layout, login, protected routes, dashboard, module cards, settings/server/audit/jobs/agent/notifications pages.
- Python mock agent contract with allowlisted mock actions only.

No real web server, Nginx, PHP, SSL, Docker, KVM, firewall, apt, systemd, SSH, RDP, VNC, or terminal feature is implemented.

## 3. Backend Status

### FastAPI App

Implemented in `backend/app/main.py`. Routers are registered for auth, core status, modules, settings, server, audit, jobs, notifications, and agent gateway.

### Database Models And Migrations

SQLAlchemy models exist in `backend/app/db/models.py`.

Implemented tables:
- `users`
- `roles`
- `permissions`
- `user_roles`
- `role_permissions`
- `modules`
- `settings`
- `jobs`
- `audit_events`
- `notifications`
- `servers`

Alembic migrations exist from `20260605_0001` through `20260605_0008`.

Default database URL is `sqlite:///./hostpilot.db`, configurable with `HOSTPILOT_DATABASE_URL`.

### Auth

Implemented:
- Argon2id password hashing via `argon2-cffi`.
- JWT bearer access tokens via `PyJWT`.
- Admin bootstrap script: `python -m app.scripts.bootstrap_admin`.
- Login endpoint.
- Current user endpoint.
- Basic in-memory login rate limiting.

Incomplete / not production-ready:
- No refresh tokens.
- No token revocation or server-side logout.
- No password reset.
- No OAuth/SSO/2FA.
- Default JWT secret is development-only unless `HOSTPILOT_SECRET_KEY` is set.

### RBAC

Implemented in `backend/app/core/rbac/permissions.py`.

RBAC is enforced in backend dependencies, not only the frontend. Seeded permissions cover Core, modules, audit, jobs, settings, agent, and notifications.

### Modules

Implemented:
- List modules.
- Get module by slug.
- Update module state.
- Valid module states: `available`, `installed`, `enabled`, `locked`.
- Seeded module registry with `core` enabled and future modules locked.

Not implemented:
- No real module loading system.
- No module package installation.
- No Nginx/PHP/SSL/Docker/KVM behavior.

### Settings

Implemented:
- List settings.
- Get setting.
- Update setting.
- Audit event on update.

Seeded settings:
- `core.product_name`
- `core.timezone`
- `core.audit_retention_days`

Settings are generic key/value records. There is no typed settings schema yet.

### Audit

Implemented:
- List audit events with filters and pagination.
- Get audit event by id.
- Audit events for login success/failure, RBAC access denied, settings update, server display update, module state update, jobs, and agent actions.

Incomplete:
- No retention policy enforcement.
- No export.
- No tamper-resistant storage.

### Jobs

Implemented:
- List jobs with filters and pagination.
- Get job by id.
- Create mock/dev job.
- Agent gateway creates and updates jobs around mock actions.

Incomplete:
- No async worker.
- No queue backend.
- No retries or scheduling.

### Notifications

Implemented:
- List own/global notifications.
- Mark one notification read.
- Mark all visible notifications read.
- Unread count.
- Notifications are created for failed login, access denied, mock agent job completed, and mock agent job failed.

Incomplete:
- No delivery channels.
- No user preferences.
- No persistence policy beyond the database table.

### Agent Gateway

Implemented:
- `GET /api/agent/status`
- `POST /api/agent/actions/mock.health`
- `POST /api/agent/actions/mock.system_info`
- `GET /api/agent/jobs/recent`
- Gateway service creates jobs, updates job results, and records audit events.

Important: the backend mock gateway executes in-process mock code only. It does not call shell commands or the operating system.

## 4. Frontend Status

### Layout

Implemented dark technical shell with sidebar, topbar, content area, notification bell/dropdown, and protected navigation.

### Login

Implemented login page. The frontend stores the JWT in `sessionStorage`. It loads the current user and permissions on app start.

### Dashboard

Implemented dashboard using backend health/status data for:
- Core status.
- Database status.
- Mock agent status.
- Local server record.
- Enabled/locked module counts.
- Recent jobs count.
- Recent audit events count.
- Agent status panel.

### Module Cards

Module cards are loaded from backend registry data. Locked modules remain disabled. Users with `modules.manage` can change registry state, but this does not enable real module features.

### Pages Implemented

- Login.
- Dashboard.
- Agent.
- Audit Log.
- Jobs.
- Notifications.
- Server.
- Settings.

No user management UI exists.

## 5. Agent Status

Implemented in `agent/webpanel_agent`.

### Mock Actions

- `mock.health`
- `mock.system_info`

### Action Contract

Request contract:
- `action`
- `payload`
- `requested_by`
- `request_id`

Response contract:
- `success`
- `status`
- `data`
- `error`
- `duration_ms`

### Allowlist / Policy

The allowlist is defined in `agent/webpanel_agent/policies/allowlist.py`.

### Real System Command Usage

No real shell/system command execution is present in the agent code. Search checks found no `subprocess`, `os.system`, `Popen`, `systemctl`, `apt`, `docker.sock`, or `shell=True` usage in backend or agent source.

## 6. Security Status

The Core Security Gate document exists at `docs/security/core-security-gate.md` and defines pass/fail checklists for release security validation.

### Auth / Session Approach

The backend uses JWT bearer tokens. The frontend stores the token in `sessionStorage`.

This is acceptable for the current local-development scaffold, but not production-ready by itself. Production work should define token lifetime, secret management, TLS assumptions, refresh/revocation strategy, and browser storage policy.

### RBAC Enforcement

RBAC is enforced in FastAPI dependencies. Frontend visibility is convenience only.

### Audit Coverage

Covered:
- Login success.
- Login failure.
- Access denied.
- Settings update.
- Server display update.
- Module state update.
- Mock job creation.
- Mock agent action requested/completed.

Incomplete:
- No audit retention enforcement.
- No immutable audit backend.

### Unsafe Patterns Found

No shell/system execution patterns were found in backend or agent source during the latest search.

### Shell/System Command Execution Check

Checked patterns:
- `subprocess`
- `os.system`
- `Popen`
- `systemctl`
- `apt`
- `docker.sock`
- `exec(`
- `shell=True`

No matches were found in backend or agent source.

## 7. Gaps And TODOs

- Production deployment is not implemented.
- No systemd/Nginx deployment files beyond placeholders.
- No user management UI.
- No password reset, 2FA, OAuth, SSO, token refresh, or token revocation.
- No real agent transport. Backend gateway currently uses in-process mock behavior.
- No real module package loading or module install lifecycle.
- No async job worker.
- No typed settings schema.
- No audit retention enforcement.
- No notification preferences or delivery channels.
- No frontend automated tests yet.
- GitHub Actions CI has been added at `.github/workflows/ci.yml` to run backend tests with migrations, agent tests, and frontend build on push and pull request to `main`.

## 8. Known Risks

- JWT default secret is development-only. `HOSTPILOT_SECRET_KEY` must be configured for non-development use.
- In-memory login rate limiting resets on process restart and is not suitable for clustered production.
- SQLite is fine for the scaffold, but production concurrency and backup strategy need design.
- `sessionStorage` token storage has browser-side XSS exposure if frontend security regresses.
- RBAC exists, but permissions are broad and early-stage.
- The frontend can show controls based on permissions, but backend RBAC remains the real security boundary.
- There is no formal threat model yet.

## 9. Exact Commands To Run

### Backend

```bash
cd webpanel/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Database Migration / Init

```bash
cd webpanel/backend
alembic upgrade head
python -m app.scripts.bootstrap_admin --email admin@example.com
```

### Frontend

```bash
cd webpanel/frontend
npm install
npm run dev
```

### Agent Mock

```bash
cd webpanel/agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m webpanel_agent.main
```

### Tests

```bash
cd webpanel/backend
python -m pytest
```

```bash
cd webpanel/agent
python -m pytest
```

```bash
cd webpanel/frontend
npm install
npm run build
```

## 10. Recommended Next Step

Recommended next step: add a minimal CI workflow that runs backend tests, agent tests, frontend build, and Alembic migration validation. This should happen before adding real module behavior, because the project now has enough Core surface area that regressions are easy to introduce.
