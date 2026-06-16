# HostPilot Project State

Last updated: 2026-06-16

## Workspace

- Official workspace: `C:\Users\Admin\OneDrive\Documentos\HostPilot_RECOVERY_CLEAN\webpanel`
- Legacy workspace to avoid: `C:\Users\Admin\OneDrive\Documentos\WebManager\webpanel`
- Current branch at time of this state update: `main`
- Current pre-state commit: `151d318135969eb194b5b5f112e7cd8d17629e8f`
- Local services:
  - Frontend: `http://127.0.0.1:5173`
  - Backend: `http://127.0.0.1:8000`

## Operational Rules

- Use only the official workspace path listed above.
- Do not move folders.
- Do not rebase.
- Do not force push.
- Before any git operation, show `git status` and current branch.
- Keep HostPilot dev services running after work:
  - Backend on `http://127.0.0.1:8000`
  - Frontend on `http://127.0.0.1:5173`
- Do not delete/recreate/reset local DB or admin password unless explicitly instructed.
- Do not touch the legacy workspace.

## Implemented Core Features

- Authentication with simple stateless bearer JWT sessions.
- Frontend token storage in `sessionStorage`.
- Backend logout audit endpoint plus client-side logout state clearing.
- RBAC permission enforcement for Core and Web APIs.
- Admin users and roles visibility.
- Admin safety guards:
  - self-deactivation blocked;
  - last active admin deactivation blocked;
  - removing own admin access blocked;
  - removing admin access from the last active admin blocked.
- Non-destructive admin bootstrap:
  - creates an admin when missing;
  - does not reset an existing admin password by default;
  - requires `--reset-password` for intentional reset.
- Module registry, settings, audit log, jobs, notifications, and Core backup archive records.
- Dev/mock-only UI actions are hidden unless explicit development mode is enabled.
- API error normalization supports FastAPI string, object, list, and validation-array detail formats.
- Agent gateway reports explicit availability states:
  - `connected`;
  - `fallback`;
  - `unavailable`.

## Implemented Web Features

- Web module route and sidebar entry.
- Web site registry model and API.
- Web site create/list/get/update/record-disable workflows.
- Web site create derives `root_path` from:
  - `web.sites.allowed_base_path`;
  - sanitized validated domain.
- User-controlled root path is not accepted during create.
- Domain validation, duplicate prevention, and root path safety checks.
- Readiness workflow:
  - `draft`;
  - `config_previewed`;
  - `ready_to_apply`;
  - `disabled`;
  - `error`.
- Nginx config preview, apply plan, and dry-run are read-only/planning flows.
- Controlled Nginx apply, disable, and re-apply use allowlisted Agent actions.
- Web Agent preflight blocks controlled actions unless a real connected Agent is available and required checks pass.
- Read-only site log viewer.
- Read-only site file browser:
  - lists metadata only;
  - loads the site root automatically on open;
  - stays within the site root;
  - prevents traversal and root-boundary escape;
  - distinguishes loading, empty directory, missing directory, and errors.
- Web UI is simplified around summary cards plus the Sites table.
- Site row Actions menu exposes:
  - Files;
  - Logs;
  - Preview;
  - Mark Ready;
  - Plan / Dry-run / Apply;
  - Disable record;
  - Disable site;
  - Re-Apply.

## Latest UI And Dashboard Changes

- Home page is a focused `Overview` dashboard instead of a crowded registry grid.
- Sidebar uses grouped navigation:
  - Overview;
  - Infrastructure;
  - Operations;
  - Modules;
  - Web;
  - Settings.
- Quick Actions live lower in the sidebar.
- Sidebar active, hover, icon, and status-card styling are aligned.
- Web module labels now reflect implemented workflows instead of scaffold/coming-soon copy.

## Known Working Items

- Backend health endpoint responds at `/health`.
- Frontend dev server responds at `/`.
- Frontend proxy reaches backend.
- Admin login works in the current local development database.
- Current local admin has `web.sites.view` and `web.sites.manage`.
- Web record creation works on Windows without Agent or Nginx.
- Web site root path is auto-derived from the configured HostPilot sites directory.
- Web list/preview/readiness/plan/dry-run flows work locally.
- Controlled Web apply is blocked locally when Agent state is `fallback`.
- Browser smoke validation showed the Web page renders site rows and row Actions without console errors.
- Local test/build run on 2026-06-16:
  - backend pytest: `108 passed`;
  - Agent pytest: `27 passed`;
  - frontend build: passed.

## Known Limits For v0.1

- v0.1 is a controlled lab/admin release, not a production installer.
- Windows dev intentionally uses Agent fallback when the local Agent is unavailable; controlled Nginx actions require a real connected Agent.
- Ubuntu lab validation could not be rerun from this workstation on 2026-06-16. The new lab SSH port at `192.168.0.64:22` is reachable, but password authentication failed for both `rattes` and `root`, so key installation is still pending.
- SSL automation is not implemented.
- PHP-FPM install/config/management is not implemented.
- Domain/DNS automation is not implemented.
- File upload/edit/delete/download are intentionally not implemented.
- Live log streaming is not implemented.
- Core backups are basic Core archive records; restore, scheduling, remote storage, and website/Nginx backup scope are not included.
- Auth/session scope is intentionally simple:
  - 60-minute stateless JWT by default;
  - no refresh tokens;
  - no server-side revocation list;
  - no SSO or MFA.

## Login And Admin Notes

- Local admin account exists: `admin@example.com`.
- Additional local admin account exists: `admin2@example.com`.
- Do not store plaintext passwords in repository docs.
- Do not reset the local admin password unless explicitly instructed.
- Do not reset or recreate the local database unless explicitly instructed.
- First-run admin creation uses `backend/app/scripts/bootstrap_admin.py`.
- Re-running bootstrap for an existing admin is non-destructive by default and does not change the password.
- To intentionally rotate an existing admin password, run bootstrap with `--reset-password`.

## Lab Notes

- Ubuntu lab SSH alias remains `hostpilot-lab`.
- Lab IP reference is `192.168.0.64`.
- Lab UI remains `http://192.168.0.64:8080`.
- Lab Core remains bound to `127.0.0.1:8000` on the lab.
- Lab Agent remains bound to `127.0.0.1:8765` on the lab.
- Local SSH alias is pointed at `rattes@192.168.0.64` with `~/.ssh/hostpilot_lab`, pending successful key installation on the lab.
