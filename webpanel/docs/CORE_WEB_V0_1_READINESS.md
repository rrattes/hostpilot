# Core + Web v0.1 Readiness

Date: 2026-06-17

Scope: HostPilot Core and Web only. Docker, KVM, SSL automation, PHP-FPM management, Remote Access, Cloudflare/DNS automation, and production installer work are outside v0.1.

## Summary

HostPilot Core + Web is ready for a controlled v0.1 lab/admin release, with clear limitations.

The product now has usable Core authentication, RBAC, admin safety guards, audit/jobs visibility, explicit Agent availability state, Web site registry records, auto-derived Web root paths, read-only Files/Logs viewers, Nginx preview/plan/dry-run, and preflight-gated controlled Nginx apply/disable/reapply flows.

Overall classification: **Ready for controlled v0.1 lab/admin use**.

Remaining limitations are known and intentionally scoped out of v0.1. The most important operational constraint is that controlled Nginx actions must run only with a real connected Agent and passing preflight on the Ubuntu lab. Windows development can create and manage records, but controlled Nginx changes are blocked while the Agent is in fallback mode.

## Validation Run

- Branch: `main`.
- Current pre-report commit: `151d318135969eb194b5b5f112e7cd8d17629e8f`.
- Backend pytest: **Ready** - `108 passed`.
- Agent pytest: **Ready** - `27 passed`.
- Frontend build: **Ready** - `npm run build` passed.
- Local backend: **Ready** - `http://127.0.0.1:8000/health` responded `200`.
- Local frontend: **Ready** - `http://127.0.0.1:5173/` responded `200`.
- Local Web API validation:
  - created site record `v01-local-20260616153459.local`;
  - derived root path `/var/www/hostpilot-sites/v01-local-20260616153459.local`;
  - generated Nginx preview;
  - marked ready to apply;
  - generated apply plan;
  - ran dry-run without writes/commands;
  - preflight reported `fallback`;
  - controlled apply was blocked with HTTP `409`.
- Browser smoke validation:
  - login through the real form worked with a temporary local validation user;
  - Web page rendered without console errors;
  - created site row appeared;
  - row Actions menu contained Files, Logs, Preview, Mark Ready, Plan / Dry-run / Apply, Disable record, Disable site, and Re-Apply;
  - controlled Agent actions were disabled while Agent state was fallback.
- Ubuntu lab validation:
  - SSH setup was completed on 2026-06-16 for `rattes@192.168.0.64`;
  - passwordless SSH through alias `hostpilot-lab` works with `~/.ssh/hostpilot_lab`;
  - OS is Ubuntu 26.04 LTS;
  - sudo access exists for `rattes`, with password prompt required;
  - HostPilot Core/Web/Agent deployment completed on the new disposable lab;
  - Core, Agent, and Nginx services are active;
  - Core health, Agent health, UI HTTP `200`, login API, and unauthenticated API proxy checks pass;
  - full Web v0.1 flow passed for `lab-test.local`, including create/list,
    Files, Logs, preview, plan, dry-run, preflight, controlled apply, disable,
    re-apply, `nginx -t`, Nginx reload, audit records, and job records;
  - detailed validation is documented in `docs/deploy/ubuntu-lab-deploy.md`.

## Readiness Matrix

| Area | Classification | Evidence | Notes |
| --- | --- | --- | --- |
| Login/auth/session | Ready | `backend/app/api/auth.py`, `frontend/src/core/auth/AuthProvider.tsx`, `frontend/src/core/api/client.ts` | v0.1 uses simple stateless 60-minute bearer tokens in `sessionStorage`. Logout clears client state immediately and calls the backend audit endpoint when possible. Expired/invalid authenticated API calls clear local auth state. |
| Password policy | Ready | `backend/app/core/auth/security.py` | Enforces length, lower/upper/digit/punctuation. |
| Login rate limiting | Ready | `backend/app/core/auth/rate_limit.py`, `backend/app/api/auth.py` | In-memory limiter is adequate for v0.1 lab/admin use. A shared limiter is later production work. |
| Admin bootstrap | Ready | `backend/app/scripts/bootstrap_admin.py`, `backend/tests/test_bootstrap_admin.py` | Existing admin passwords are not reset unless `--reset-password` is provided. |
| Admin safety guards | Ready | `backend/app/api/admin.py`, `backend/tests/test_admin_users.py` | Blocks self-deactivation, last active admin deactivation, own admin role removal, and removing admin access from the last active admin. |
| RBAC backend enforcement | Ready | `backend/app/core/rbac/permissions.py`, endpoint dependencies in `backend/app/api/*.py` | Core/Web APIs consistently use permissions. |
| RBAC seeds/migrations | Ready | Alembic seed and repair migrations | Core and Web permissions are seeded and repaired for admin role access. |
| Users UI/API | Ready | `backend/app/api/admin.py`, `frontend/src/pages/UsersPage.tsx` | Admin user management works for v0.1. Role definition editing remains out of scope. |
| Roles UI/API | Ready | `backend/app/api/admin.py`, `frontend/src/pages/RolesPage.tsx` | Roles and permissions are inspectable. |
| Audit log | Ready | `backend/app/api/audit.py`, `backend/app/core/audit/events.py`, `frontend/src/pages/AuditLogPage.tsx` | Implemented Core/Web mutations record audit events. |
| Jobs | Ready | `backend/app/api/jobs.py`, `frontend/src/pages/JobsPage.tsx` | Job listing is visible. Dev-only mock job creation is hidden unless explicit dev mode is enabled. |
| Notifications | Ready | `backend/app/api/notifications.py`, `frontend/src/pages/NotificationsPage.tsx` | List/read/read-all flows exist and are RBAC-protected. |
| Core backups | Nice to have later | `backend/app/api/backups.py`, `backend/app/core/backups/service.py`, `frontend/src/pages/BackupsPage.tsx` | Basic Core archive creation exists. Restore, scheduling, remote storage, and Web/Nginx backup scope are later work. |
| Agent health/status | Ready | `backend/app/core/agent_gateway/service.py`, `backend/app/api/agent.py`, `frontend/src/pages/AgentPage.tsx`, `frontend/src/pages/DashboardPage.tsx` | States are explicit: `connected`, `fallback`, `unavailable`. UI shows whether Web actions use a real Agent. |
| Agent allowlist | Ready | `agent/webpanel_agent/policies/allowlist.py`, `backend/app/core/agent_gateway/mock_client.py` | No arbitrary command execution; allowed actions are explicit. |
| Dev/mock-only UI | Ready | `backend/app/api/agent.py`, `frontend/src/pages/JobsPage.tsx`, `frontend/src/pages/AgentPage.tsx` | Hidden by default and labeled `Development only` when enabled. |
| Web module visibility | Ready | `backend/app/api/web.py`, `frontend/src/core/routes/App.tsx` | Web route respects module state and permissions. |
| Web site create/list/get/update/disable record | Ready | `backend/app/api/web.py`, `frontend/src/pages/WebPage.tsx` | Registry workflows work and do not require Agent/Nginx for record creation. |
| Web root path derivation | Ready | `backend/app/api/web.py`, `backend/tests/test_web.py`, `frontend/src/pages/WebPage.tsx` | Create derives `root_path` from `web.sites.allowed_base_path` plus validated domain. Client cannot override root path. |
| Web validation | Ready | `backend/app/api/web.py`, `backend/tests/test_web.py` | Domain, duplicate, safe-path, custom allowed-base, and traversal rejection paths are covered. |
| Nginx preview | Ready | `backend/app/api/web.py`, `frontend/src/pages/WebPage.tsx` | Preview returns text only and does not write. |
| Readiness workflow | Ready | `backend/app/api/web.py`, `frontend/src/pages/WebPage.tsx` | Draft/previewed/ready/disabled/error workflow exists. |
| Apply plan | Ready | `backend/app/api/web.py`, `frontend/src/pages/WebPage.tsx` | Plan is read-only and requires `ready_to_apply`. |
| Dry-run | Ready | `backend/app/api/web.py`, `frontend/src/pages/WebPage.tsx` | Does not execute commands or write files. |
| Web Agent preflight | Ready | `backend/app/api/web.py`, `frontend/src/pages/WebPage.tsx`, `backend/tests/test_web.py` | Checks Agent state, required allowlisted actions, allowed Web base, Nginx config base, commands, and path assumptions. Blocks controlled actions when not ready. |
| Controlled apply | Ready for controlled lab v0.1 | `backend/app/api/web.py`, `agent/webpanel_agent/actions/nginx.py`, `agent/tests/test_nginx_apply_action.py`, `docs/deploy/ubuntu-lab-deploy.md` | Backend/Agent tests pass and the full apply flow passed on the Ubuntu lab with real connected Agent/preflight. |
| Controlled disable/reapply | Ready for controlled lab v0.1 | `backend/app/api/web.py`, `agent/webpanel_agent/actions/nginx.py`, `backend/tests/test_web.py`, `docs/deploy/ubuntu-lab-deploy.md` | Disable and re-apply passed on the Ubuntu lab with real connected Agent/preflight. |
| Files read-only viewer | Ready | `backend/app/api/web.py`, `frontend/src/pages/WebPage.tsx`, `agent/webpanel_agent/actions/nginx.py` | Path constrained, metadata-only, paginated/limited, and root-loading behavior exists. |
| Logs read-only viewer | Ready | `backend/app/api/web.py`, `frontend/src/pages/WebPage.tsx`, `agent/webpanel_agent/actions/nginx.py` | Read-only, max-line constrained, path constrained. |
| Frontend loading/error states | Ready | `frontend/src/core/api/client.ts`, Core/Web pages | API errors are normalized and loading states reset in the reviewed flows. |
| API response consistency | Ready | `frontend/src/core/api/client.ts` | Handles FastAPI detail strings, lists, objects, and validation arrays. |
| Migrations/seeds | Ready | Alembic versions through current head | Covers Core, RBAC, notifications, backups, Web, validation, readiness, and permission repair. |
| Windows dev flow | Ready | Local validation on 2026-06-16 | Web record creation, list, preview, readiness, plan, and dry-run work without Agent/Nginx. Controlled apply blocks in fallback. |
| Ubuntu lab flow | Ready for controlled lab v0.1 | `docs/deploy/ubuntu-lab-deploy.md` | New lab `192.168.0.64` passed Core health `200`, Agent health `200`, UI `200`, backend pytest `108 passed`, Agent pytest `27 passed`, frontend build, and the full Web v0.1 flow. |

## Fixed v0.1 Blockers

- Agent state is explicit and no longer ambiguous.
- Web allowed base path is propagated to apply/file payloads.
- Admin bootstrap is non-destructive by default.
- Dev/mock-only UI actions are gated by explicit development mode.
- API errors are normalized for common FastAPI detail shapes.
- Web preflight blocks controlled actions when real Agent is unavailable.
- Admin lockout safety guards are enforced in the backend.
- Web create derives root paths server-side and does not trust client root path input.
- Web page is organized around the actual Sites workflow instead of scaffold copy.

## Auth/Session Scope

v0.1 decision: **keep a simple 60-minute stateless JWT session.**

- The backend issues bearer access tokens from `POST /api/core/auth/login`.
- Default expiry remains 60 minutes and is configurable through the existing access-token setting.
- The frontend stores the token in `sessionStorage`.
- Logout is client-authoritative for v0.1:
  - the UI clears token, current user, and permission state immediately;
  - when a valid token is still available, it calls `POST /api/core/auth/logout` for audit.
- Expired or invalid tokens clear local auth state and return the user to login.
- v0.1 does not include refresh tokens, server-side token revocation, SSO, MFA, or long-lived remember-me sessions.
- Operators must treat bearer tokens as sensitive until expiry.

## Remaining Limitations

- v0.1 is not a production deployment story.
- The new Ubuntu lab is validated for the Core/Web v0.1 flow, but it remains a disposable test host.
- SSL automation is not implemented.
- PHP-FPM installation/configuration/management is not implemented.
- WordPress/Ghost application profiles are not implemented.
- Domain/DNS automation is not implemented.
- File upload/edit/delete/download are intentionally absent.
- Live log streaming is not implemented.
- Core backup restore/scheduling/remote-storage flows are not implemented.
- Role definition editing is not included.
- Docker, KVM, and Remote Access modules are not included in v0.1.
- Windows dev fallback is useful for local testing but is not a real connected Agent.

## Ordered Fix Plan After v0.1

1. Add a production deployment hardening plan separate from the lab installer.
2. Expand Core backup scope with restore, scheduling, and remote storage decisions.
3. Add SSL automation only after the Nginx controlled apply/rollback model is stable.
4. Add PHP-FPM runtime management only after defining OS/package boundaries.
5. Add role-definition editing only if v0.1 operators need custom roles.
