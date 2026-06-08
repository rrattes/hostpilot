# HostPilot Core Audit Coverage Matrix

Date: 2026-06-08

Status legend: Covered, Partial, Missing, Not Required.

## Matrix

| Core workflow | Expected audit event(s) | Status | Notes |
| --- | --- | --- | --- |
| Login success | `auth.login.succeeded` | Covered | Records user id as actor/target on successful login. |
| Login failure | `auth.login.failed`, `auth.login.rate_limited` | Covered | Failed login and rate limit attempts are recorded as failures. |
| Logout/session behavior | `auth.logout.requested` | Covered | Logout remains stateless bearer behavior; audit records the logout request and mode. |
| Password change success | `auth.password_change.succeeded` | Covered | Current-user password change records success. |
| Password change failure | `auth.password_change.failed` | Covered | Wrong current password and password policy failures are audited. |
| Access denied/RBAC denial | `rbac.access_denied` | Covered | Backend permission dependency records denied permission. |
| User create | `users.created` | Covered | Admin-created users are audited with target user and role metadata. |
| User active status update/disable | `users.active_status.updated` | Covered | Enable/disable changes include previous and new status. |
| User role change | `users.roles.updated` | Covered | Previous and new role slugs are recorded. |
| User password reset | `users.password_reset` | Covered | Manual admin password reset is audited. |
| User list/view | None | Not Required | Read-only user listing is RBAC-protected but not currently audit-required. |
| Roles/permissions view | None | Not Required | Read-only RBAC metadata view is RBAC-protected; no audit event required yet. |
| Settings update | `settings.updated` | Covered | Setting key and previous value are recorded. |
| Server record update | `server.display.updated` | Covered | Local server display changes include previous name/description. |
| Module state update | `modules.state.updated` | Covered | Previous and new module state are recorded. |
| Job create | `jobs.mock.created` | Covered | Manual mock job creation is audited. |
| Job update/failure | `agent.action.completed` for Agent jobs | Partial | Agent-driven job completion/failure is audited. Generic job update/retry worker does not exist yet. |
| Agent action success | `agent.action.requested`, `agent.action.completed` | Covered | Request and completion events are recorded for successful allowlisted actions. |
| Agent action failure | `agent.action.requested`, `agent.action.completed` | Covered | Unknown/failing actions record failed jobs and failure outcome. |
| Notification read | `notifications.read` | Covered | Single notification read mutation is audited. |
| Notification read-all | `notifications.read_all` | Covered | Bulk visible notification read mutation records count. |
| Core backup success | `core.backup.created` | Covered | Successful backup records archive path and included files. |
| Core backup failure | `core.backup.failed` | Covered | Failed backup records safe reason/error type and target id when available. |
| Audit event list/view | None | Not Required | Audit reads are RBAC-protected; read audit of audit-log browsing is not currently required for Core. |

## Gaps And Follow-Up

- Generic job update, retry, scheduling, and worker failure audit events are not applicable yet because those job capabilities do not exist.
- Roles/permissions view is read-only and not audited. Add an event later only if policy requires tracking RBAC metadata reads.
- User listing is read-only and not audited. Add an event later only if policy requires admin-directory read tracking.
- Audit log reads are not audited. This can be revisited before production release if audit-log access itself must be tracked.

## Fixes Made During Matrix Review

- Added `notifications.read` audit event for single notification read mutations.
- Added `notifications.read_all` audit event for bulk visible notification read mutations.
- Added backend tests confirming both notification audit events.
