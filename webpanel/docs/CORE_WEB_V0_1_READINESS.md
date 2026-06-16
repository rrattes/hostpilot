# Core + Web v0.1 Readiness Audit

Date: 2026-06-12

Scope: HostPilot Core and Web only. No Docker, KVM, SSL automation, PHP management, or Remote Access modules are included in this audit.

## Summary

HostPilot Core + Web is close to a credible v0.1 for a controlled lab/admin product, but it is not yet ready to call a real usable v0.1 without a short hardening pass. The backend and Agent test suites are healthy, the Web workflows are intentionally constrained, and the UI now exposes the Core/Web workflows clearly. The main blockers are operational product gaps around Agent availability, bootstrap/first-run safety, API/config consistency, and a few user-facing state/error edges.

Overall classification: **Needs fix before v0.1**.

## Validation Run

- `git status`: clean except this readiness report after authoring; branch `main`.
- Backend pytest: **Ready** - `88 passed`.
- Agent pytest: **Ready** - `27 passed`.
- Frontend build: **Ready** - `npm run build` passed.
- Local backend: **Ready** - `http://127.0.0.1:8000/health` responds `200`.
- Local frontend: **Ready** - `http://127.0.0.1:5173/` responds `200`.

## Blockers Found

1. **Agent availability is not a first-class product state.**  
   References: `backend/app/core/agent_gateway/service.py:26`, `backend/app/core/agent_gateway/service.py:34`, `backend/app/core/agent_gateway/service.py:98`, `backend/app/core/agent_gateway/service.py:102`; `frontend/src/pages/AgentPage.tsx:74`.  
   In dev/test, missing local Agent falls back to mock behavior and may report `status: ok` with `mode: mock-fallback`. That is helpful for Windows dev, but for v0.1 the UI and apply flows need a clear product-grade distinction between "local Agent connected" and "fallback/dev mock". Otherwise operators can think Web actions are available when real Agent-backed filesystem/Nginx work will fail or be simulated.

2. **Web allowed base path setting is not consistently used by Agent payloads.**  
   References: `backend/app/api/web.py:1088`, `backend/app/api/web.py:1094`, `backend/app/api/web.py:1225`, `backend/app/api/web.py:1253`; migration `backend/alembic/versions/20260611_0012_web_site_validation.py:20`.  
   Site create/update/readiness validates against `web.sites.allowed_base_path`, but `_agent_apply_payload` and `_agent_files_payload` still send `DEFAULT_WEB_SITES_BASE_PATH`. If the setting is changed, backend validation may pass while Agent actions reject or browse the wrong allowed boundary. This is a v0.1 correctness blocker.

3. **First-run/admin bootstrap remains operator-manual and can reset credentials.**  
   References: `backend/app/scripts/bootstrap_admin.py:15`, `backend/app/scripts/bootstrap_admin.py:29`, `backend/app/scripts/bootstrap_admin.py:47`; state rule in `docs/PROJECT_STATE.md`.  
   The script is useful, but it updates an existing admin password whenever run. v0.1 needs documented first-run behavior and guardrails so operators do not accidentally rotate the admin password or depend on tribal knowledge.

4. **Core status still reports mock-oriented Agent fields.**  
   References: `backend/app/api/core_status.py:37`, `backend/app/api/core_status.py:40`, `backend/app/api/core_status.py:71`, `backend/app/api/core_status.py:74`; dashboard usage `frontend/src/pages/DashboardPage.tsx:84`.  
   Core health returns `agent_mock_status` and `agent_mode: mock` even after the local Agent path exists. For v0.1, the status model should represent real local Agent connectivity and fallback state.

5. **Nginx/Web apply production readiness depends on lab/service setup, not fully productized UX.**  
   References: `docs/deploy/ubuntu-lab-deploy.md:108`; `backend/app/api/web.py:1173`, `backend/app/api/web.py:1190`, `backend/app/api/web.py:1194`; `agent/webpanel_agent/actions/nginx.py:103`, `agent/webpanel_agent/actions/nginx.py:165`.  
   Controlled apply/disable are constrained and tested, but v0.1 needs an operator-visible preflight that confirms the Ubuntu Agent, paths, Nginx command, permissions, and service reload are actually available before the user reaches "Apply".

## Readiness Matrix

| Area | Classification | Evidence | Notes |
| --- | --- | --- | --- |
| Login/auth/session | Ready | `backend/app/api/auth.py:63`, `backend/app/api/auth.py:161`; `frontend/src/core/auth/AuthProvider.tsx:26`, `frontend/src/core/auth/AuthProvider.tsx:91`; `frontend/src/core/api/client.ts:35` | v0.1 uses simple stateless 60-minute bearer tokens in `sessionStorage`. Frontend logout clears token/user/permissions immediately and calls the backend logout audit endpoint when possible. Expired/invalid authenticated API calls clear local session state and redirect to login. |
| Password policy | Ready | `backend/app/core/auth/security.py:65` | Enforces length, lower/upper/digit/punctuation. |
| Login rate limiting | Ready | `backend/app/core/auth/rate_limit.py:11`; `backend/app/api/auth.py:66` | In-memory limiter exists. For multi-process production, later centralization would be nice. |
| Admin bootstrap | Needs fix before v0.1 | `backend/app/scripts/bootstrap_admin.py:15`, `backend/app/scripts/bootstrap_admin.py:47` | Works, but reruns update password. Needs first-run docs/guardrail. |
| RBAC backend enforcement | Ready | `backend/app/core/rbac/permissions.py:29`; endpoint dependencies in `backend/app/api/*.py` | Core/Web APIs consistently use `require_permission`. |
| RBAC seeds/migrations | Ready | `backend/alembic/versions/20260605_0003_seed_core_rbac.py:22`; `backend/alembic/versions/20260612_0014_repair_web_sites_admin_permissions.py:21` | Core and Web permissions are seeded/repairable. |
| Users UI/API | Ready | `backend/app/api/admin.py:97`, `frontend/src/pages/UsersPage.tsx:41` | CRUD-style admin user management exists. Nice later: self-deactivation guard and stronger API error surfacing. |
| Roles UI/API | Ready | `backend/app/api/admin.py:73`, `frontend/src/pages/RolesPage.tsx:67` | Roles/permissions are inspectable. Editing role definitions is not required for v0.1. |
| Audit log | Ready | `backend/app/api/audit.py:47`, `backend/app/core/audit/events.py:8`, `frontend/src/pages/AuditLogPage.tsx:22` | Audit events are recorded/readable. |
| Jobs | Needs fix before v0.1 | `backend/app/api/jobs.py:57`, `backend/app/api/jobs.py:89`, `frontend/src/pages/JobsPage.tsx:42` | Listing works. "Create mock job" is still a dev artifact and is protected only by `jobs.view`; hide/rename/remove before v0.1 or mark clearly as dev-only. |
| Notifications | Ready | `backend/app/api/notifications.py:36`, `backend/app/api/notifications.py:101`, `frontend/src/pages/NotificationsPage.tsx:41` | List/read/read-all flows exist and are RBAC-protected. |
| Core backups | Nice to have later | `backend/app/api/backups.py:40`, `backend/app/core/backups/service.py:32`, `frontend/src/pages/BackupsPage.tsx:104` | Backup metadata/archive creation works. Restore/download/scheduling are intentionally absent; okay if v0.1 labels this as metadata/archive only. |
| Agent health/status | Needs fix before v0.1 | `backend/app/core/agent_gateway/service.py:26`, `backend/app/api/agent.py:45`, `frontend/src/pages/AgentPage.tsx:74` | Needs real/fallback/unavailable UX clarity and service startup docs. |
| Agent allowlist | Ready | `agent/webpanel_agent/policies/allowlist.py:1`, `backend/app/core/agent_gateway/mock_client.py:7` | No arbitrary command execution; allowed actions are explicit. |
| Web module visibility | Ready | `backend/app/api/web.py:254`, `frontend/src/core/routes/App.tsx:215` | Web route respects module state and permissions. |
| Web site create/list/get/update/disable record | Ready | `backend/app/api/web.py:273`, `backend/app/api/web.py:425`, `backend/app/api/web.py:477`, `backend/app/api/web.py:529`; `frontend/src/pages/WebPage.tsx:161` | Registry workflows work and are records-only until controlled apply. |
| Web validation | Needs fix before v0.1 | `backend/app/api/web.py:1088`, `backend/app/api/web.py:1094`, `backend/app/api/web.py:1225`, `backend/app/api/web.py:1253` | Validation is strong, but setting is not propagated to Agent payloads. |
| Nginx preview | Ready | `backend/app/api/web.py:563`, `backend/app/api/web.py:1146`, `frontend/src/pages/WebPage.tsx:636` | Preview returns text only and does not write. |
| Readiness workflow | Ready | `backend/app/api/web.py:602`, `backend/app/api/web.py:612`, `backend/app/api/web.py:995`; `frontend/src/pages/WebPage.tsx:1270` | Draft/previewed/ready/disabled/error workflow exists. |
| Apply plan | Ready | `backend/app/api/web.py:652`, `backend/app/api/web.py:1173`, `frontend/src/pages/WebPage.tsx:736` | Plan is read-only and requires `ready_to_apply`. |
| Dry-run | Ready | `backend/app/api/web.py:688`, `backend/app/api/web.py:1201`, `frontend/src/pages/WebPage.tsx:275` | Does not execute commands or write files. |
| Controlled apply | Needs fix before v0.1 | `backend/app/api/web.py:746`, `agent/webpanel_agent/actions/nginx.py:103`, `agent/tests/test_nginx_apply_action.py:63` | Safety is strong, tests pass. Product readiness depends on Agent availability clarity and allowed base path consistency. |
| Controlled disable/reapply | Needs fix before v0.1 | `backend/app/api/web.py:814`, `backend/app/api/web.py:883`, `agent/webpanel_agent/actions/nginx.py:165` | Same Agent/product-state concerns as apply. |
| Files read-only viewer | Needs fix before v0.1 | `backend/app/api/web.py:352`, `frontend/src/pages/WebPage.tsx:137`, `frontend/src/pages/WebPage.tsx:1005`, `agent/webpanel_agent/actions/nginx.py:250` | Safety and loading states are good. Needs Agent availability clarity and allowed base path setting propagation. |
| Logs read-only viewer | Ready | `backend/app/api/web.py:292`, `frontend/src/pages/WebPage.tsx:376`, `agent/webpanel_agent/actions/nginx.py:230` | Read-only, max line constrained, path constrained. |
| Frontend loading/error states | Needs fix before v0.1 | Good examples: `frontend/src/pages/WebPage.tsx:183`, `frontend/src/pages/WebPage.tsx:395`, `frontend/src/pages/WebPage.tsx:422`; weaker generic catches: `frontend/src/pages/UsersPage.tsx:41`, `frontend/src/pages/NotificationsPage.tsx:24` | Web is mostly robust. Core admin pages should expose API detail consistently. |
| API response consistency | Needs fix before v0.1 | `backend/app/api/web.py:407`; frontend API error parser in `frontend/src/core/api/client.ts:44` | Basic string `detail` works. Some FastAPI validation errors are arrays/objects, which may produce weak messages. |
| Migrations/seeds | Ready | Alembic versions `20260605_0001` through `20260612_0014` | Covers Core, RBAC, notifications, backups, Web, validation, readiness, permission repair. |
| Windows dev flow | Ready | Current tests/build pass on Windows; service URLs verified | Good for development. Local Agent absence remains expected but must be explicit in UI/docs. |
| Ubuntu lab flow | Needs fix before v0.1 | `docs/deploy/ubuntu-lab-deploy.md:108` | Lab docs exist and controlled apply was validated earlier, but v0.1 needs repeatable checklist for the current feature set including disable/reapply/files/logs. |

## Ordered Fix Plan

1. **Fix Web allowed-base propagation to Agent.**  
   Use `_allowed_base_path(db)` in apply/file payloads and align apply plan/readiness with the configured setting. Add backend tests for custom `web.sites.allowed_base_path`.

2. **Make Agent product state explicit.**  
   Replace "ok mock-fallback" ambiguity with a clear status model: `connected`, `fallback`, `unavailable`. Surface it in Dashboard, Agent page, and Web action modals. Disable controlled apply/disable/reapply when real Agent is unavailable outside dev.

3. **Productize first-run admin bootstrap.**  
   Document first-run admin creation, add a non-reset mode or explicit `--reset-password` flag, and update docs to reinforce: do not reset local DB/admin password unless explicitly instructed.

4. **Remove or gate dev-only mock actions from v0.1 UI.**  
   Hide "Create mock job" and mock Agent action execution unless a dev mode flag is active, or rename them unmistakably as development tools.

5. **Improve API error normalization.**  
   Update frontend API client to render FastAPI validation details consistently for list/object/string `detail`; update Users/Settings/Notifications/Jobs pages to preserve API messages.

6. **Add v0.1 Agent/Ubuntu preflight.**  
   Add a read-only backend/UI preflight that checks Agent reachable, allowed actions, Nginx path assumptions, configured allowed webroot base, and command availability without changing server state.

7. **Refresh Ubuntu lab validation docs for the current Web feature set.**  
   Include apply, disable, reapply, files, logs, audit/job records, created paths, and rollback expectations.

8. **Add small admin safety guards.**
   Prevent accidental self-deactivation/role lockout or at least show strong confirmation in the UI.

9. **Label backup scope in product copy and docs.**
    Make clear that Core backups are Core DB/config archives only, with no restore, scheduler, website, Nginx, SSL, or remote storage support in v0.1.

## Auth/Session Scope

v0.1 decision: **keep a simple 60-minute stateless JWT session.**

- The backend issues bearer access tokens from `POST /api/core/auth/login`; the default expiry is 60 minutes and remains configurable through the existing access-token settings.
- The frontend stores the token in `sessionStorage`, so a browser/tab session is intentionally short-lived and does not persist like `localStorage`.
- Logout is client-authoritative for v0.1: the UI clears token, current user, and permission state immediately. When a valid token is still available, it also calls `POST /api/core/auth/logout` so the backend can record the audit event.
- Expired or invalid tokens are handled by clearing local auth state and returning the user to the login screen.
- v0.1 does not include refresh tokens, server-side token revocation, SSO, MFA, or long-lived remember-me sessions. A copied token remains cryptographically usable until it expires, so operators should treat bearer tokens as sensitive.

## v0.1 Decision

Recommended decision: **Do not mark Core + Web as v0.1-ready yet.**  

The codebase has a solid tested foundation, especially around RBAC, audit/job recording, Web safety boundaries, and Agent allowlisting. The remaining work is not broad feature expansion; it is a focused readiness pass to make operational state honest, configuration consistent, and first-run/admin behavior safer.
