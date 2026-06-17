# HostPilot Production Hardening Plan

Date: 2026-06-17

Scope: HostPilot Core + Web deployment hardening only. This plan does not mark
the current lab release as production-ready and does not add SSL automation,
Docker, KVM, PHP-FPM management, WordPress/Ghost profiles, or new modules.

## Current Lab-Supported State

HostPilot Core + Web v0.1 is validated for a controlled Ubuntu lab environment.

- Supported lab OS: Ubuntu 26.04 LTS.
- Lab UI target: Nginx on port `8080`.
- Core service: FastAPI/Uvicorn bound to `127.0.0.1:8000`.
- Agent service: bound to `127.0.0.1:8765`.
- Database: local SQLite.
- Web managed site base: `/var/www/hostpilot-sites`.
- HostPilot-managed Nginx config path: `/etc/nginx/sites-available/hostpilot`.
- Controlled Web actions require a connected Agent and passing preflight.
- Validated lab checks include Core health `200`, Agent health `200`, UI `200`,
  backend pytest `108 passed`, Agent pytest `27 passed`, frontend build passed,
  and the Web v0.1 flow passed.

The lab state is appropriate for controlled admin evaluation. It is not a
production security or operations model.

## Required Production Work

### Supported OS and Runtime

- Define the supported production operating systems, starting with one Ubuntu
  LTS target.
- Pin Python, Node.js, Nginx, and system package versions or version ranges.
- Document CPU, memory, disk, and filesystem requirements.
- Add a production compatibility check that verifies runtime versions before
  install or upgrade.

### Non-Root Deployment Model

- Run Core and frontend build artifacts under a dedicated unprivileged
  `hostpilot` service account.
- Keep writable application data under a dedicated directory such as
  `/var/lib/hostpilot`.
- Keep logs under `/var/log/hostpilot`.
- Keep static/frontend assets under a read-only deployment directory after
  install.
- Ensure the Core process cannot write to Nginx configuration directories
  directly.

### systemd Hardening

- Add hardened unit files for Core and Agent.
- For Core, use protections such as `NoNewPrivileges=true`,
  `PrivateTmp=true`, `ProtectSystem=strict`, and explicit `ReadWritePaths`.
- For Agent, use the smallest writable paths and elevated privileges needed for
  allowlisted Web actions only.
- Add restart limits, watchdog behavior, environment file ownership rules, and
  clear service dependency ordering.
- Validate service hardening with `systemd-analyze security`.

### Nginx and TLS Strategy

- Define the production listener model for HostPilot UI and managed sites.
- Decide whether HostPilot UI TLS is terminated by Nginx, an upstream proxy, or
  an external load balancer.
- Add a certificate lifecycle plan before enabling production TLS automation.
- Keep managed-site Nginx configs isolated under the HostPilot-managed config
  path.
- Preserve the rule that HostPilot must not touch unrelated Nginx configs.
- Require `nginx -t` before reload and rollback on validation failure.

### Secrets Management

- Move secrets out of ad hoc environment files into a documented production
  secret store or locked-down systemd environment file.
- Define ownership and permissions for JWT secrets, database credentials, Agent
  shared secrets, and any future TLS/provider credentials.
- Add secret rotation procedures.
- Ensure secrets are never written to logs, docs, release notes, or Git.

### Database Strategy Beyond SQLite

- Select a production database target, likely PostgreSQL.
- Add migration and configuration guidance for PostgreSQL.
- Define backup, restore, retention, and point-in-time recovery expectations.
- Add connection pooling and health checks.
- Define a supported SQLite-to-production migration path or explicitly state
  that SQLite is lab/dev only.

### Backup and Restore Strategy

- Define what must be backed up: database, HostPilot config, secrets metadata,
  managed Nginx configs, audit records, and relevant application state.
- Add tested restore procedures, not just archive creation.
- Add retention policy and storage targets.
- Add restore drills to the release checklist.
- Document what HostPilot does not back up, including unrelated host data and
  unmanaged Nginx configs.

### Agent Privilege Model

- Keep Agent action execution allowlisted and typed.
- Split read-only Agent actions from privileged mutation actions.
- Require backend authorization, typed confirmation, preflight, job records, and
  audit events for privileged actions.
- Prefer narrowly scoped sudoers rules for specific Agent helper commands over
  unrestricted root execution.
- Keep Agent bound to localhost or a protected private interface only.
- Add production guidance for Agent authentication, request signing, timeout
  limits, and replay protection.

### Firewall and Network Ports

- Document required inbound ports:
  - public UI/API reverse proxy port, normally `443`;
  - optional `80` only for redirects or certificate challenges;
  - managed site ports as explicitly configured.
- Keep Core and Agent private on localhost or protected internal interfaces.
- Block direct public access to Core and Agent ports.
- Add firewall validation steps for UFW/nftables and cloud security groups.

### Logs and Audit Retention

- Define retention for application logs, Agent logs, Nginx logs, job records,
  and audit records.
- Add log rotation policy.
- Protect audit logs from ordinary application mutation paths.
- Add export/archival strategy for compliance or incident review.
- Define minimum fields required for privileged Web actions.

### Upgrade and Rollback Procedure

- Package releases with versioned artifacts and checksums.
- Before upgrade, require database backup and config snapshot.
- Run migrations with a documented rollback boundary.
- Keep the previous release available for service rollback.
- Validate Core health, Agent health, UI, login, and Web preflight after
  upgrade.
- Document what cannot be rolled back automatically, especially database schema
  migrations after destructive changes.

### Health Checks

- Keep Core `/health` lightweight and unauthenticated.
- Keep Agent `/health` local/private.
- Add readiness checks for database connectivity, migration state, Agent
  reachability, Nginx availability, and writable path assumptions.
- Expose clear states: healthy, degraded, unavailable.
- Add operational runbooks for failed health and preflight checks.

## Minimum Production Checklist

- Supported OS/runtime documented and validated.
- Dedicated non-root service account created.
- Core and Agent systemd units hardened.
- Core and Agent private ports not exposed publicly.
- UI served through Nginx with a defined TLS strategy.
- Production database selected, configured, backed up, and restore-tested.
- Secrets stored with strict permissions and rotation procedure.
- Agent privilege model documented and constrained with allowlisted actions.
- Firewall rules verified.
- Logs and audit retention configured.
- Upgrade and rollback process tested.
- Health/readiness checks pass.
- Controlled Web apply/disable/reapply tested on a production-like staging host.

## Future Nice-To-Have Items

- Automated TLS issuance and renewal after the Nginx production model is stable.
- PostgreSQL high availability and point-in-time recovery.
- Centralized log shipping and alerting.
- Signed release artifacts.
- Blue/green or canary upgrades.
- Multi-node Agent inventory.
- Expanded role editor and approval workflows for privileged actions.
- Application profiles such as WordPress and Ghost after PHP/runtime boundaries
  are defined.
