# HostPilot Core Release Checklist

Status legend: Done, Partial, Pending.

## Core Readiness

| Area | Status | Notes |
| --- | --- | --- |
| Auth hardening | Done | Secret key is mandatory outside dev/test, token lifetime is configurable, password policy and current-user password change exist, logout is documented as stateless bearer behavior. |
| RBAC | Done | Core permissions and route guards exist for current Core surfaces, including backup create/view. |
| Audit coverage | Partial | Login, password changes, RBAC denial, settings/server edits, jobs, agent actions, user management, and backups audit key events. Broader audit review is still needed before release. |
| Jobs | Done | Core job records, listing/detail, mock job creation, and agent job records exist. |
| Notifications | Done | Notifications list/read/read-all, permissions, and event creation paths exist. |
| Module registry | Done | Registry/state model exists with locked future module placeholders and protected state updates. |
| Agent mock/transport | Partial | Local HTTP agent transport, health, request contract validation, timeout, allowlist, and dev fallback exist. No privileged actions or service installer beyond lab templates. |
| Backup basics | Partial | Manual Core backup create/list exists for SQLite and Core config/state files. No restore, schedule, download UI, cloud, or external backup support. |
| CI | Done | GitHub Actions workflow validates backend, agent, and frontend under `webpanel/`. |
| Lab installer | Partial | Repeatable Ubuntu 26.04 lab installer/check scripts exist. Python 3.14 dependency compatibility still requires isolated Python 3.13. |
| Security gate | Done | Core Security Gate documentation exists with pass/fail checks. |
| Known non-goals before modules | Done | No website, Nginx, SSL, Docker, KVM, package update, terminal, remote shell, SSO/OAuth/2FA, cloud backup, scheduled backup, or restore automation is in Core. |

## Pending Core Items

- Complete an audit coverage review and close any missing audit events for Core workflows.
- Resolve Ubuntu 26.04 Python 3.14 dependency compatibility or formally document Python 3.13 as the supported Core runtime.
- Add focused frontend automated coverage for shell navigation and Core admin pages.
- Reconcile the local branch with `origin/main` and validate CI on GitHub.
- Decide whether Core backup needs a download endpoint or keep it explicitly filesystem-only before module work.

## Next 5 Technical Tasks

1. Resolve the Ubuntu 26.04 Python runtime decision: update dependencies for Python 3.14 or pin/document Python 3.13 as supported.
2. Run the Core Security Gate and record results in `docs/project-state/current-state.md`.
3. Add frontend tests for authenticated routing, sidebar utility links, Users, and Backups pages.
4. Perform an audit-event matrix review for auth, RBAC, settings, users, jobs, agent, notifications, and backups.
5. Reconcile with `origin/main`, push the current branch, and validate GitHub Actions CI.
