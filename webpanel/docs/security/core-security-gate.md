# HostPilot Core Security Gate

This document defines the minimum security pass/fail gate before HostPilot Core is considered releasable.

## Dependency Scanning

- [ ] Pass: backend and agent dependencies are pinned and scanned with `pip-audit` or equivalent.
- [ ] Pass: critical and high findings are fixed or have written risk acceptance.
- [ ] Fail: any unresolved critical or high dependency finding remains undocumented.

## Python Security Linting

- [ ] Pass: `backend/app` and `agent/webpanel_agent` are scanned with Bandit or equivalent.
- [ ] Pass: no unsafe shell execution, hardcoded production secrets, or auth bypass patterns are introduced.
- [ ] Fail: any high-risk lint finding remains unresolved or unaccepted.

## Frontend Audit

- [ ] Pass: `npm audit` is reviewed in `frontend/`.
- [ ] Pass: `npm run build` succeeds.
- [ ] Pass: token storage and protected route behavior are reviewed.
- [ ] Fail: frontend authorization is treated as the only access-control boundary.

## OWASP ZAP Baseline

- [ ] Pass: ZAP baseline runs against a local or staging deployment.
- [ ] Pass: auth, API, and frontend routes are included in scope.
- [ ] Fail: unresolved high-risk alerts exist for injection, CORS, missing headers, cookies, or information disclosure.

## Nessus/OpenVAS Readiness

- [ ] Pass: host-level scan is run only against an approved local or staging target.
- [ ] Pass: no unexpected services are exposed.
- [ ] Pass: OS/package findings are patched or risk-accepted.
- [ ] Fail: scan artifacts contain secrets or unreviewed sensitive data.

## Auth And Session Checks

- [ ] Pass: non-development deployments require a non-default `HOSTPILOT_SECRET_KEY`.
- [ ] Pass: passwords use Argon2id hashing.
- [ ] Pass: login success, login failure, and access denied events are audited.
- [ ] Fail: default development secrets are usable in release.
- [ ] Fail: token lifetime, logout, revocation, refresh, and storage policy are undefined for release.

## RBAC And IDOR/BOLA Manual Tests

- [ ] Pass: each protected endpoint is tested as admin, operator, viewer, and unauthenticated user.
- [ ] Pass: backend permissions reject unauthorized direct API calls.
- [ ] Pass: object ids cannot be accessed across unauthorized user or role contexts.
- [ ] Fail: any protected action relies only on frontend visibility checks.

## Agent Allowlist Validation

- [ ] Pass: only expected mock actions are allowlisted.
- [ ] Pass: unknown actions fail closed.
- [ ] Pass: no shell, package manager, service manager, Docker, SSH, or arbitrary command execution path exists.
- [ ] Fail: any agent route can execute arbitrary commands or modify real OS state.

## Secrets And Local File Permissions

- [ ] Pass: `.env`, local databases, logs, keys, `.dev/`, and runtime state are ignored by Git.
- [ ] Pass: no production secrets are committed.
- [ ] Pass: local database files are not required as release credentials.
- [ ] Fail: secrets, scan reports, backups, or logs are stored in public web roots.

## Future Nginx, TLS, And Security Headers Checks

- [ ] Pass: TLS is required for non-local deployments.
- [ ] Pass: HTTP redirects to HTTPS.
- [ ] Pass: HSTS, CSP, X-Content-Type-Options, Referrer-Policy, and frame protections are configured.
- [ ] Pass: reverse proxy request size and timeout limits are defined.
- [ ] Fail: backend APIs are exposed directly when release design requires proxy-only access.

## Core Release Criteria

- [ ] Pass: backend tests pass.
- [ ] Pass: agent tests pass.
- [ ] Pass: frontend build passes.
- [ ] Pass: dependency scanning, security linting, frontend audit, and ZAP baseline have no unresolved high-risk findings.
- [ ] Pass: RBAC, IDOR/BOLA, agent allowlist, secrets, and file permission checks pass.
- [ ] Fail: any critical or high finding remains unresolved without written risk acceptance.
- [ ] Fail: arbitrary command execution is introduced.
- [ ] Fail: release depends on local runtime state or development secrets.
