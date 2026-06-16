# HostPilot Project State

Last updated: 2026-06-12

## Workspace

- Official workspace: `C:\Users\Admin\OneDrive\Documentos\HostPilot_RECOVERY_CLEAN\webpanel`
- Legacy workspace to avoid: `C:\Users\Admin\OneDrive\Documentos\WebManager\webpanel`
- Current branch at time of this state update: `main`
- Current pre-state commit: `e7dbc57f96c786d221c967861e6b75cd45c71948`
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

## Implemented Modules And Features

- Core platform shell:
  - Authentication and admin users/roles.
  - RBAC permission checks.
  - Module registry.
  - Settings.
  - Audit events.
  - Jobs.
  - Notifications.
  - Core backup records.
  - Mock/local Agent gateway.
- Dashboard/UI:
  - Modern `Overview` landing page.
  - Grouped sidebar navigation.
  - Sidebar visual standardization with consistent icons, hover, active, and focus states.
  - Summary cards, system activity chart, jobs donut, recent activity list, and compact modules snapshot.
- Web module:
  - Web module page and sidebar route.
  - Web site registry model/API.
  - Site create/list/get/record-disable.
  - Domain and safe root path validation.
  - Readiness workflow and statuses.
  - Nginx config preview.
  - Nginx apply plan preview.
  - Dry-run apply.
  - Controlled Nginx apply via Agent.
  - Controlled disable and re-apply flows.
  - Read-only site log viewer.
  - Read-only site file browser.
  - File browser now loads the site root automatically when opened.

## Known Working Items

- Backend health endpoint responds at `/health`.
- Frontend dev server responds at `/`.
- Frontend proxy reaches backend; unauthenticated core status returns expected `401`.
- Admin login works in the current local development database.
- Web site row actions are visible after site records exist.
- Web file browser opens from a site row and automatically starts loading the site root.
- When the local Agent is unavailable, Web file/log actions show clear errors rather than hanging.
- Frontend build has passed after the latest UI/sidebar changes.
- Backend pytest previously passed after the latest backend Web file-browser/API changes.

## Known Broken Or Pending Items

- Local Agent is not currently running in normal Windows dev flow, so Agent-backed Web actions may return dev fallback errors until the Agent is started.
- Web file/log viewers are read-only and depend on Agent availability for real filesystem/log data.
- SSL automation is not implemented.
- PHP-FPM install/config/management is not implemented.
- Domain/DNS automation is not implemented.
- Upload/edit/delete/download in the file browser are intentionally not implemented.
- Live log streaming is not implemented.
- Real Nginx validation should continue to be done on the Ubuntu lab, not on Windows.

## Current Web Module Status

- Web module is active in the UI.
- Site registry stores records only until controlled apply is requested.
- Nginx preview/plan/dry-run are preview/simulation flows unless controlled Agent apply is explicitly confirmed.
- Controlled apply/disable/reapply are allowlisted Agent actions, not arbitrary shell execution.
- File browser:
  - Lists metadata only.
  - Stays within the site `root_path`.
  - Prevents traversal/root-boundary escape.
  - Shows distinct states for loading, empty directory, missing site root, and errors.
- Logs viewer:
  - Reads only HostPilot-managed access/error log paths.
  - Enforces max line limits.

## Login And Admin Notes

- Local admin account exists: `admin@example.com`.
- Additional local admin account exists: `admin2@example.com`.
- Do not store plaintext passwords in repository docs.
- Do not reset the local admin password unless explicitly instructed.
- Do not reset or recreate the local database unless explicitly instructed.
- First-run admin creation uses `backend/app/scripts/bootstrap_admin.py`.
- Re-running bootstrap for an existing admin is non-destructive by default and does not change the password.
- To intentionally rotate an existing admin password, run bootstrap with `--reset-password`.

## Latest UI And Dashboard Changes

- Home page was redesigned from crowded registry-style cards into a focused `Overview`.
- Sidebar was reorganized into grouped sections:
  - Overview
  - Infrastructure
  - Operations
  - Modules
  - Settings
- Quick Actions were added lower in the sidebar:
  - Run Audit
  - View Logs
  - Create Backup
  - New Job
- Sidebar icons/colors were standardized so main sections and menu items match the Quick Actions visual language.
- Active sidebar item uses stronger cyan/blue accent.
- Inactive sidebar items remain softer but readable.

## GitHub Save Notes

- This state file is intended to document the current local project state before pushing accumulated commits to GitHub.
- Product code should not be changed as part of this state snapshot.
