# HostPilot Core Release Checklist

Date: 2026-06-08

Status legend: Done, Partial, Pending.

## Core Readiness

| Area | Status | Notes |
| --- | --- | --- |
| Auth/session | Partial | Login, current-user lookup, Argon2id hashing, mandatory non-dev secret, configurable token lifetime, password policy, current-user password change, and client-side stateless logout behavior exist. No refresh tokens, server-side revocation, 2FA, SSO, or password reset. |
| User management | Done | Admin UI and backend endpoints exist to list users, create users, enable/disable users, assign roles, and manually reset passwords. |
| Roles/permissions | Partial | Read-only Roles & Permissions UI exists and shows role metadata defensively. No custom roles, permission editor, or dedicated role-management permission beyond `core.admin`. |
| RBAC enforcement | Done | Backend permission dependencies protect Core APIs; frontend visibility is convenience only. Admin, operator, viewer roles are seeded. |
| Audit log | Partial | Audit coverage matrix exists at `docs/project-state/audit-coverage-matrix.md`. Core mutation events are covered for current implemented workflows, including notification read/read-all. No retention enforcement, export, or tamper-resistant storage. |
| Jobs | Partial | Core job records, listing/detail, mock job creation, and agent job records exist. No async worker, external queue, retries, or scheduler. |
| Notifications | Partial | Notification list/read/read-all, unread count, permissions, and event creation paths exist. No delivery channels, preferences, or retention policy. |
| Module registry | Done | Registry/state model exists with Core enabled and future module placeholders locked. No real module install/load lifecycle before Web module. |
| Settings/server record | Done | Settings and local server display record APIs/UI exist with RBAC and audit coverage for edits. |
| Agent mock/transport | Partial | Local HTTP agent transport, health, request/response validation, timeout, request_id handling, allowlist enforcement, and dev fallback exist. No privileged or real OS actions. |
| Core backup | Partial | Manual Core backup API/UI creates and lists local SQLite/Core config backup metadata and artifacts. No restore, download endpoint, schedule, cloud backup, website backup, Nginx backup, or SSL backup. |
| Dev runner | Done | Windows `scripts/dev.ps1` and `scripts/test.ps1` exist under `webpanel/` for local dev/test flow. |
| CI | Done | GitHub Actions workflow exists at `.github/workflows/ci.yml` for backend tests/migrations, agent tests, and frontend build. |
| Ubuntu lab deploy | Partial | Ubuntu lab docs and systemd/Nginx templates exist and have been lab-validated. Lab runtime is pinned to isolated Python 3.13 under `/opt/hostpilot/python`; it remains lab-only, not production deployment guidance. |
| Security gate | Partial | `docs/security/core-security-gate.md` exists and local results are recorded in `docs/project-state/security-gate-results-2026-06-08.md`. Python dependency scan, Python security lint, ZAP, Nessus/OpenVAS, and formal IDOR/BOLA matrix remain pending. |
| Installer lab | Partial | Repeatable Ubuntu 26.04 lab installer and check scripts exist. The Python runtime decision is resolved for lab use: create backend and Agent venvs from isolated Python 3.13 under `/opt/hostpilot/python`. Python 3.14 migration remains deferred. |

## Remaining Core Blockers Before Web Module

- Validate the Python 3.13 lab runtime through the updated installer/check scripts on the Ubuntu 26.04 host.
- Complete pending Security Gate items: Python dependency scan, Python security lint, ZAP baseline, Nessus/OpenVAS readiness, and formal RBAC/IDOR/BOLA matrix.
- Add focused frontend regression tests for authenticated routing and Core admin pages.
- Address audit release-hardening gaps: retention enforcement, export policy, tamper-resistant storage decision, and optional read-access audit policy.
- Validate GitHub Actions on the remote branch after reconciliation with `origin/main`.
- Decide whether Core backup remains filesystem-only or needs a safe download endpoint before Web module work.

## Non-Goals Before Web Module

- No website hosting or website backup features.
- No Nginx site management beyond lab deploy templates.
- No SSL certificate automation.
- No Docker, KVM, package manager, firewall, terminal, remote shell, SSH, RDP, or VNC features.
- No privileged Agent actions or arbitrary command execution.
- No OAuth, SSO, 2FA, self-registration, or password reset email.
- No scheduled, cloud, restore, website, Nginx, or SSL backup automation.
- No custom role creation or permission editor.

## Next 5 Technical Tasks

1. Re-run `deploy/scripts/install-lab.sh` and `deploy/scripts/check-lab.sh` on the Ubuntu 26.04 lab host to validate the Python 3.13 pin end-to-end.
2. Add `pip-audit` and Bandit execution to local/CI security validation or document an equivalent scanner.
3. Add frontend tests for login-protected routing, sidebar utility links, Users, Roles, Backups, and Settings account security.
4. Build the formal RBAC/IDOR/BOLA matrix for auth/session, users, roles, settings, server record, jobs, notifications, agent, and backups.
5. Reconcile with `origin/main`, push, and validate GitHub Actions CI on GitHub.
