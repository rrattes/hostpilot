# Development Log - 2026-06-08

## Repository State

- Canonical local repository root: `C:\Users\Admin\OneDrive\Documentos\WebManager`.
- Canonical project directory: `webpanel/`.
- Git remote: `https://github.com/rrattes/hostpilot.git`.
- Branch validated locally: `main`.
- A nested Git repository was found at `webpanel/.git` and renamed to `webpanel/.git.backup` so `webpanel/` is treated as a normal project directory under the root repository.

## File Availability Validation

Repository file validation was performed from the root repository.

- Tracked files checked: `118`.
- Missing tracked files: `0`.
- Result: all files tracked by the repository are present on disk.

The canonical application files are available under `webpanel/`, including:

- Backend FastAPI app, tests, Alembic configuration, and migrations.
- Frontend React/Vite/TypeScript app, package manifest, lockfile, source files, and build configuration.
- Agent mock package and tests.
- Project documentation under `webpanel/docs/`.
- Deployment placeholder directories under `webpanel/deploy/`.
- Windows development/test scripts under `webpanel/scripts/`.

## Validation Commands

The following checks passed locally after the dashboard/sidebar UI refinement:

```powershell
cd webpanel/backend
python -m pytest
```

Result: `30 passed`.

```powershell
cd webpanel/agent
python -m pytest
```

Result: `3 passed`.

```powershell
cd webpanel/frontend
npm run build
```

Result: production build completed successfully.

```powershell
git ls-files
```

Result summary: `118` tracked files, `0` missing tracked files.

## Latest Tasks Completed

- Verified the project structure and confirmed the main application is under `webpanel/`.
- Confirmed backend and agent tests pass.
- Reinstalled frontend dependencies after detecting an incomplete `node_modules` installation for `lucide-react`.
- Confirmed frontend production build passes.
- Renamed the accidental nested Git repository from `webpanel/.git` to `webpanel/.git.backup`.
- Started backend locally at `http://127.0.0.1:8000`.
- Started frontend locally at `http://127.0.0.1:5173`.
- Created a local development admin user through the backend bootstrap script.
- Confirmed login works through the backend API.
- Refined the HostPilot dashboard visual design with tighter summary cards, denser module registry cards, improved borders/shadows/hover states, and reduced awkward empty space.
- Refined the sidebar navigation hierarchy so Dashboard, Server, Agent, Notifications, Audit Log, and Jobs are primary navigation items.
- Moved Settings into the bottom utility area while preserving the existing `/settings` route.
- Repositioned Core as the active platform context in the sidebar footer.

## Current Development Ports

- Backend: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Frontend: `http://127.0.0.1:5173`

## Local-Only Notes

- `webpanel/backend/hostpilot.db` was modified locally when the development admin user was created. This file contains local runtime state and should not be committed as part of this log update.
- The local development password was intentionally not written to this GitHub log.
- Some duplicate/untracked files and directories currently exist at the repository root, such as root-level `README.md`, `agent/`, `docs/`, and `deploy/`. They were left uncommitted pending a separate cleanup decision.
- The local branch is ahead of and behind `origin/main`; remote reconciliation is still pending.
- No frontend automated tests exist yet for the dashboard/sidebar shell.

## Windows Dev/Test Script Validation

Validation was performed from the `webpanel/` project root.

```powershell
.\scripts\test.ps1
```

Result:

- Backend tests ran successfully: `30 passed`.
- Agent tests ran successfully: `3 passed`.
- Frontend `npm ci` and production build ran successfully.
- Test runner summary reported all checks passed.

The first test runner attempt failed during frontend `npm ci` with a Windows `EPERM` file-lock error because an older local Vite process was still holding a native dependency under `frontend/node_modules`. After stopping the stale development processes, the same script completed successfully without script changes.

```powershell
.\scripts\dev.ps1
```

Result:

- Backend started on `http://127.0.0.1:8000`.
- API docs were exposed at `http://127.0.0.1:8000/docs`.
- Frontend started on `http://127.0.0.1:5173`.
- Logs were written under `.dev/logs/`.
- Validation processes were stopped after confirming both development ports.

## Ubuntu Lab Deployment Validation

Validation was performed against the lab server on `2026-06-08`.

- SSH alias: `hostpilot-lab`.
- Confirmed SSH user: `root`.
- Confirmed lab IP: `192.168.0.64`.
- Confirmed OS: Ubuntu 26.04 LTS.
- Project deployed to `/opt/hostpilot` with project root `/opt/hostpilot/webpanel`.
- Runtime user/group created: `hostpilot`.
- Secrets stored outside git under `/etc/hostpilot/core.env`.

Packages and runtimes confirmed on the lab host:

- `python3` 3.14.4.
- Isolated Python 3.13.13 under `/opt/hostpilot/python`.
- `python3-venv`, `python3-pip`, `nodejs` 22.22.1, `npm` 9.2.0, `nginx`
  1.28.3, `git`, `curl`, and `uv` 0.11.19.

The backend dependencies did not install on Ubuntu's default Python 3.14 because
the pinned `pydantic-core` build does not yet support that interpreter. The lab
was validated with isolated Python 3.13.13 installed by `uv`; this is a current
deployment compatibility gap, not a product feature change.

Lab validation commands:

```bash
cd /opt/hostpilot/webpanel/backend
python -m pytest
```

Result: `43 passed`.

```bash
cd /opt/hostpilot/webpanel/agent
python -m pytest
```

Result: `6 passed`.

```bash
cd /opt/hostpilot/webpanel/frontend
npm run build
```

Result: production build completed successfully.

Services created from deploy templates:

- `hostpilot-agent.service`: enabled and active.
- `hostpilot-core.service`: enabled and active.
- Nginx lab config installed at `/etc/nginx/conf.d/hostpilot-lab.conf`.

Validated lab bindings and URLs:

- Core: `127.0.0.1:8000`.
- Agent: `127.0.0.1:8765`.
- Nginx lab frontend: `http://192.168.0.64:8080/`.
- Agent health returned `status: ok`.
- Core health returned `status: ok`.
- Nginx frontend returned HTTP `200`.
- Nginx `/api` proxy returned HTTP `401` for an unauthenticated protected
  endpoint, confirming proxy traffic reached Core.

Lab-only note: root SSH was used for this validation because the target was an
isolated lab server. This should not be treated as the production deployment
operating model.

## Next Recommended Technical Step

Resolve the Ubuntu 26.04 Python 3.14 dependency compatibility gap, then
reconcile the local branch with `origin/main` and add focused frontend automated
coverage for the dashboard/sidebar shell.

## Project State Refresh - 2026-06-11

The project state documentation was refreshed after the Core readiness, security
gate, audit matrix, backup, auth/session, roles, and deployment work.

Latest Core items recorded:

- Auth/session basics hardened with mandatory non-dev secret, configurable token
  lifetime, password change endpoint, minimum password policy, and audit events.
- Core user management implemented for listing, creating, enabling/disabling,
  assigning roles, and manual password reset.
- Roles & Permissions read-only UI implemented and repaired so it handles
  loading, empty, and error states.
- Core Backup create/list workflow implemented with persisted metadata, real
  backup artifact creation, RBAC permissions, and audit events.
- Local Agent transport implemented over loopback HTTP with allowlisted mock
  actions and backend development fallback.
- Ubuntu lab deployment assets now pin runtime strategy to isolated Python 3.13
  under `/opt/hostpilot/python`.
- Core Security Gate, audit coverage matrix, and Core readiness decision are now
  documented under `webpanel/docs/project-state/`.

Latest recorded validation:

- Backend pytest: `48 passed`.
- Agent pytest: `6 passed`.
- Frontend tests: no `test` script is configured.
- Frontend build: production build completed successfully.

Validation attempted during this state refresh:

- Backend pytest: passed with `48 passed` after setting `TEMP` and `TMP` to a
  workspace-local temporary directory. The local backend `.venv` launcher points
  to a Python executable that is no longer present, so the available Codex
  Python runtime was used with the backend venv site-packages.
- Agent pytest: not valid in the current checkout; pytest collected `0` tests
  because tracked agent package/test files are currently missing from the
  working tree.
- Frontend tests: no-op because no `test` script is configured.
- Frontend build: passed.

Current local Git issue found during the refresh:

- Local `main` is ahead of `origin/main` by Core implementation commits and
  behind `origin/main` by remote-only commits.
- The working tree currently shows missing tracked files, including
  `.github/workflows/ci.yml`, `webpanel/.gitignore`, `webpanel/README.md`, and
  several agent packaging/test files.
- `webpanel/.git.backup/` is present as untracked local backup data from the
  earlier nested Git repository cleanup.
- These missing tracked files were not staged as part of this documentation
  update and should be reconciled before publishing destructive changes.

Current known limitations:

- Security Gate remains partial until dependency scan, Python security linting,
  OWASP ZAP, Nessus/OpenVAS readiness, and formal RBAC/IDOR/BOLA checks are
  completed.
- Ubuntu lab should be revalidated end-to-end with `install-lab.sh` and
  `check-lab.sh` after the Python 3.13 runtime pin.
- No automated frontend regression test suite exists yet.
- Core is Ready with Known Gaps for Web module work, not production release.

Next recommended technical step:

Reconcile local `main` with `origin/main`, restore or intentionally remove the
missing tracked files, and then push a clean branch. After Git state is clean,
add focused frontend regression tests for the authenticated Core shell and Core
admin pages.
