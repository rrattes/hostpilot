# HostPilot File Map

## Backend

- `backend/app/main.py`: FastAPI application setup and router registration.
- `backend/app/api/auth.py`: Login, current user, and current roles/permissions endpoints.
- `backend/app/api/admin.py`: Minimal Core admin status endpoint for RBAC enforcement.
- `backend/app/api/core_status.py`: Aggregated Core health/status endpoint.
- `backend/app/api/modules.py`: Module registry list/detail/update endpoints.
- `backend/app/api/settings.py`: Core settings list/get/update endpoints.
- `backend/app/api/servers.py`: Local server record get/update endpoints.
- `backend/app/api/audit.py`: Audit event list/detail endpoints.
- `backend/app/api/jobs.py`: Jobs list/detail and mock job endpoint.
- `backend/app/api/notifications.py`: Notification list and mark-read endpoints.
- `backend/app/api/agent.py`: Mock Agent Gateway endpoints.
- `backend/app/db/base.py`: SQLAlchemy declarative base and timestamp mixin.
- `backend/app/db/models.py`: SQLAlchemy models for Core tables.
- `backend/app/db/session.py`: SQLAlchemy engine/session configuration.
- `backend/app/core/auth/security.py`: Argon2id password hashing and JWT helpers.
- `backend/app/core/auth/dependencies.py`: Current-user FastAPI dependency.
- `backend/app/core/auth/rate_limit.py`: In-memory login rate limiting.
- `backend/app/core/rbac/permissions.py`: Permission lookup and RBAC dependency.
- `backend/app/core/audit/events.py`: Audit event creation helper.
- `backend/app/core/notifications/events.py`: Notification creation helper.
- `backend/app/core/confirmations/models.py`: Reusable confirmation requirement helper.
- `backend/app/core/agent_gateway/contracts.py`: Backend-side agent request/response contracts.
- `backend/app/core/agent_gateway/mock_client.py`: In-process mock agent action runner.
- `backend/app/core/agent_gateway/service.py`: Agent gateway orchestration with jobs and audit.
- `backend/app/scripts/bootstrap_admin.py`: Initial admin user bootstrap script.
- `backend/alembic.ini`: Alembic configuration.
- `backend/alembic/env.py`: Alembic environment loading app metadata.
- `backend/alembic/versions/`: Database schema and seed migrations.
- `backend/tests/`: Backend unit/API tests.
- `backend/requirements.txt`: Backend Python dependencies.

## Frontend

- `frontend/src/main.tsx`: React entrypoint.
- `frontend/src/core/routes/App.tsx`: Lightweight protected-route orchestration.
- `frontend/src/core/auth/AuthProvider.tsx`: Frontend auth state, token storage, current user, and permissions.
- `frontend/src/core/auth/types.ts`: Auth-related TypeScript types.
- `frontend/src/core/api/client.ts`: Shared fetch wrapper.
- `frontend/src/core/api/agent.ts`: Agent Gateway API client.
- `frontend/src/core/api/audit.ts`: Audit API client.
- `frontend/src/core/api/jobs.ts`: Jobs API client.
- `frontend/src/core/api/modules.ts`: Module registry API client.
- `frontend/src/core/api/notifications.ts`: Notifications API client.
- `frontend/src/core/api/server.ts`: Local server API client.
- `frontend/src/core/api/settings.ts`: Settings API client.
- `frontend/src/core/api/status.ts`: Core health/status API client.
- `frontend/src/core/layout/AppLayout.tsx`: Sidebar, topbar, navigation, user info, notification bell.
- `frontend/src/core/modules/moduleCatalog.ts`: Module presentation helpers and descriptions.
- `frontend/src/core/theme/global.css`: Global dark technical visual styling.
- `frontend/src/components/ConfirmationModal.tsx`: Reusable safe confirmation modal.
- `frontend/src/pages/LoginPage.tsx`: Login page.
- `frontend/src/pages/DashboardPage.tsx`: Core dashboard and module cards.
- `frontend/src/pages/AgentPage.tsx`: Mock Agent status/actions/recent jobs page.
- `frontend/src/pages/AuditLogPage.tsx`: Audit log page.
- `frontend/src/pages/JobsPage.tsx`: Jobs page.
- `frontend/src/pages/NotificationsPage.tsx`: Notifications page.
- `frontend/src/pages/ServerPage.tsx`: Local server display record page.
- `frontend/src/pages/SettingsPage.tsx`: Core settings page.
- `frontend/package.json`: Frontend scripts and dependencies.
- `frontend/vite.config.ts`: Vite config with dev proxy to backend.

## Agent

- `agent/webpanel_agent/contracts.py`: Agent action request/response dataclasses.
- `agent/webpanel_agent/actions/mock.py`: Mock action runner.
- `agent/webpanel_agent/policies/allowlist.py`: Allowlisted mock actions.
- `agent/webpanel_agent/mock/system_info.py`: Static mock system information.
- `agent/webpanel_agent/main.py`: Minimal mock agent entrypoint.
- `agent/tests/test_mock_agent.py`: Agent tests.
- `agent/requirements.txt`: Agent Python dependencies.

## Documentation

- `README.md`: Project overview and local development commands.
- `docs/architecture/core-platform.md`: Core Platform concept.
- `docs/security/security-principles.md`: Security principles and non-goals.
- `docs/modules/module-contract.md`: Future module registration contract.
- `docs/project-state/current-state.md`: Current factual project state report.
- `docs/project-state/file-map.md`: Important file map for reviewers.

## Deployment Placeholders

- `deploy/systemd/.gitkeep`: Placeholder for future service units.
- `deploy/nginx/.gitkeep`: Placeholder for future Nginx deployment config.
- `deploy/scripts/.gitkeep`: Placeholder for future deployment scripts.
