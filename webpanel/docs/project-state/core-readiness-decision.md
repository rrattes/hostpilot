# HostPilot Core Readiness Decision

Date: 2026-06-08

Decision: Ready with Known Gaps for starting the Web module.

## Decision Basis

HostPilot Core has enough stable foundation to begin Web module work without adding unrelated Core features first. The current Core provides authenticated access, backend RBAC enforcement, user management, read-only roles/permissions visibility, audit log coverage for implemented Core mutations, jobs, notifications, module registry scaffolding, settings/server record management, local Agent mock/transport, Core backup basics, Windows dev/test scripts, GitHub Actions CI, Ubuntu lab deploy templates, and lab installer/check scripts.

This is not a production release decision. Core remains not fully releasable until the pending security gate, lab, frontend test automation, and release-hardening items are closed or risk-accepted.

## Blocking Issues For Web Module

None found in the current local review.

## Non-Blocking Known Gaps

- Frontend has no automated test script yet; `npm run test --if-present` completes without running tests.
- Security Gate remains partial: Python dependency scan, Python security linting, OWASP ZAP baseline, Nessus/OpenVAS readiness, and formal RBAC/IDOR/BOLA matrix are pending.
- Ubuntu 26.04 lab runtime pin to isolated Python 3.13 still needs end-to-end revalidation on the lab host with `install-lab.sh` and `check-lab.sh`.
- Audit release hardening remains pending: retention enforcement, export policy, tamper-resistant storage decision, and optional read-access audit policy.
- Core backup remains manual and filesystem-oriented; no restore, download endpoint, scheduling, cloud, website, Nginx, or SSL backup support.
- Jobs remain synchronous/simple for current Core flows; no async worker, external queue, retries, or scheduler.
- Auth/session remains Core-basic only; no refresh tokens, server-side revocation, password reset, OAuth/SSO, or 2FA.

## Validation Run

| Check | Result |
| --- | --- |
| Backend pytest | Pass: 48 passed. |
| Agent pytest | Pass: 6 passed. |
| Frontend tests | Not present: no frontend `test` script is defined. |
| Frontend build | Pass: production build completed. |

## Reviewed Inputs

- `docs/project-state/core-release-checklist.md`
- `docs/project-state/security-gate-results-2026-06-08.md`
- `docs/project-state/audit-coverage-matrix.md`
- Current frontend `package.json` scripts and local validation results.

## Recommended Next Task

Start the Web module skeleton only after defining its contract against the existing Core module registry, RBAC, audit, job, notification, backup, and Agent allowlist boundaries. Keep Web module work behind locked/available module state until its own security and audit surfaces are defined.
