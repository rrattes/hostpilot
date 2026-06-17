# HostPilot Ubuntu Lab Deploy

This is a lab deployment workflow for Ubuntu Server 26.04. It includes a
repeatable lab installer, but it is not a production installer.

## Assumptions

- Repository checkout target: `/opt/hostpilot`.
- Project root: `/opt/hostpilot/webpanel`.
- Runtime user and group: `hostpilot`.
- Core API listens on `127.0.0.1:8000`.
- Local Agent listens on `127.0.0.1:8765`.
- Nginx exposes the lab UI on port `8080`.
- Frontend is built before Nginx serves `frontend/dist`.
- Secrets are supplied outside git through `/etc/hostpilot/core.env`.
- Ubuntu 26.04 currently ships Python 3.14. HostPilot was validated in this lab
  with an isolated Python 3.13 runtime under `/opt/hostpilot/python`.
- Runtime decision: the Ubuntu 26.04 lab uses `/opt/hostpilot/python` as the
  application Python runtime for Core and Agent venv creation. The app does not
  rely on Ubuntu's system Python 3.14 yet because pinned backend dependencies
  have not been migrated and validated on Python 3.14.
- Root SSH was used only for the `192.168.0.64` lab validation. Production
  deployment should use a least-privilege operating procedure.

## Prepare Runtime Files

1. Create a dedicated runtime user and application directory using your lab
   operating procedure.
2. Place the repository at `/opt/hostpilot`.
3. Ensure the `hostpilot` user owns files that need runtime write access.
4. Keep secrets outside the repository.

Example environment values for `/etc/hostpilot/core.env`:

```ini
HOSTPILOT_SECRET_KEY=replace-with-a-long-random-secret
HOSTPILOT_ACCESS_TOKEN_MINUTES=60
HOSTPILOT_AGENT_TIMEOUT_SECONDS=2
```

## Repeatable Lab Installer

Run the installer from the `webpanel/` project root on the Ubuntu 26.04 lab
host:

```bash
sudo ./deploy/scripts/install-lab.sh
```

The installer:

- Installs or confirms `python3`, `python3-venv`, `python3-pip`, `nodejs`,
  `npm`, `nginx`, `git`, `curl`, and `uv`.
- Deploys the current `webpanel/` tree to `/opt/hostpilot/webpanel`.
- Preserves `/etc/hostpilot/core.env` and `/etc/hostpilot/agent.env`.
- Preserves an existing lab SQLite database at
  `/opt/hostpilot/webpanel/backend/hostpilot.db` when redeploying.
- Uses isolated Python 3.13 under `/opt/hostpilot/python` for backend and Agent
  virtual environments.
- Verifies that both backend and Agent virtual environments use Python 3.13.
- Installs backend and Agent dependencies.
- Runs Alembic migrations.
- Builds the frontend with `npm ci` and `npm run build`.
- Installs only the HostPilot systemd units:
  `hostpilot-core.service` and `hostpilot-agent.service`.
- Installs only the HostPilot Nginx lab config:
  `/etc/nginx/conf.d/hostpilot-lab.conf`.
- Starts/restarts HostPilot services and reloads Nginx.

The installer does not configure SSL, domains, production hardening, unrelated
Nginx sites, or real Agent OS actions.

Run the validation helper after installation:

```bash
sudo /opt/hostpilot/webpanel/deploy/scripts/check-lab.sh
```

Expected summary: all checks pass for Core, Agent, Nginx, loopback bindings,
Core/Agent Python 3.13 runtime, Core health, Agent health, and the lab UI.

## Build Backend

Manual backend setup remains available for debugging:

```bash
cd /opt/hostpilot/webpanel/backend
/opt/hostpilot/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

The Core service template binds Uvicorn to `127.0.0.1:8000`.

## Build Agent

Manual Agent setup remains available for debugging:

```bash
cd /opt/hostpilot/webpanel/agent
/opt/hostpilot/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

The Agent template starts `python -m webpanel_agent.main` and is expected to bind
to `127.0.0.1` only. The current agent exposes mock actions plus the controlled
`web.nginx.apply_site_config` action, constrained to HostPilot-managed Nginx and
webroot paths.

## Build Frontend

Manual frontend setup remains available for debugging:

```bash
cd /opt/hostpilot/webpanel/frontend
npm ci
npm run build
```

Nginx serves `/opt/hostpilot/webpanel/frontend/dist`.

## Review Templates

- Systemd Core template:
  `webpanel/deploy/systemd/hostpilot-core.service`
- Systemd Agent template:
  `webpanel/deploy/systemd/hostpilot-agent.service`
- Nginx lab config:
  `webpanel/deploy/nginx/hostpilot-lab.conf`

Review paths, user names, ports, and hardening options before copying templates
into real system locations.

## Lab Activation Outline

1. Run `sudo ./deploy/scripts/install-lab.sh` from the `webpanel/` project root.
2. Run `sudo /opt/hostpilot/webpanel/deploy/scripts/check-lab.sh`.
3. Open `http://<lab-host>:8080`.

## Validation

Expected local checks on the Ubuntu host:

```bash
curl http://127.0.0.1:8765/health
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8080/
curl http://127.0.0.1:8080/api/agent/status
```

Expected exposed lab URL:

```text
http://<lab-host>:8080
```

## 2026-06-08 Lab Validation

Validation target:

- SSH alias: `hostpilot-lab`.
- Lab IP: `192.168.0.64`.
- Confirmed SSH user: `root`.
- Confirmed OS: Ubuntu 26.04 LTS.

Installed packages/runtime:

- `python3` 3.14.4 from Ubuntu.
- Isolated Python 3.13.13 under `/opt/hostpilot/python`.
- `python3-venv`, `python3-pip`, `nodejs`, `npm`, `nginx`, `git`, and `curl`.
- `uv` 0.11.19 was used to install the isolated Python 3.13 runtime for lab
  validation.

Services created from templates:

- `hostpilot-agent.service`: enabled and active.
- `hostpilot-core.service`: enabled and active.
- Nginx lab config installed as `/etc/nginx/conf.d/hostpilot-lab.conf`.

Validated bindings and URLs:

- Core: `127.0.0.1:8000`.
- Agent: `127.0.0.1:8765`.
- Nginx lab frontend: `http://192.168.0.64:8080/`.
- Agent health: `curl http://127.0.0.1:8765/health` returned `status: ok`.
- Core health: `curl http://127.0.0.1:8000/health` returned `status: ok`.
- Nginx frontend returned HTTP `200`.
- Nginx `/api` proxy returned HTTP `401` for an unauthenticated protected
  endpoint, confirming traffic reached Core.

Validation commands passed on the lab host:

```bash
cd /opt/hostpilot/webpanel/backend
python -m pytest
```

Result: `43 passed`.

```bash
cd /opt/hostpilot/webpanel/agent
python -m pytest
```

Result: `6 passed`.

```bash
cd /opt/hostpilot/webpanel/frontend
npm run build
```

Result: production build completed successfully.

## 2026-06-08 Revalidation

The lab deployment was revalidated after the latest frontend dashboard card
layout refinement.

Validation target:

- SSH alias: `hostpilot-lab`.
- Lab IP: `192.168.0.64`.
- Confirmed SSH user: `root`.
- Confirmed OS: Ubuntu 26.04 LTS.

Confirmed packages/runtime:

- `python3` 3.14.4 from Ubuntu.
- Isolated Python 3.13.13 under `/opt/hostpilot/python`.
- `python3-venv`, `python3-pip`, `nodejs` 22.22.1, `npm` 9.2.0, `nginx`
  1.28.3, `git`, `curl`, and `uv`.

Deployment validation:

- Current repository archive was deployed to `/opt/hostpilot`.
- Backend and Agent virtual environments were recreated with isolated Python
  3.13.13.
- Backend dependencies installed successfully.
- Agent dependencies installed successfully.
- Alembic migrations completed successfully.
- Frontend dependencies installed with `npm ci`.
- Frontend production build completed successfully.
- Existing systemd and Nginx lab templates were installed.

Service and URL validation:

- `hostpilot-core.service`: enabled and active.
- `hostpilot-agent.service`: enabled and active.
- Nginx: active.
- Core bound to `127.0.0.1:8000`.
- Agent bound to `127.0.0.1:8765`.
- Nginx exposed the lab UI on `0.0.0.0:8080`.
- `curl http://127.0.0.1:8765/health` returned Agent `status: ok`.
- `curl http://127.0.0.1:8000/health` returned Core `status: ok`.
- `curl http://127.0.0.1:8080/` returned HTTP `200`.
- `curl http://192.168.0.64:8080/` returned HTTP `200`.
- `curl http://127.0.0.1:8080/api/agent/status` returned HTTP `401`, which
  is expected without an auth token and confirms the `/api` proxy reaches Core.

Validation commands passed on the lab host:

```bash
cd /opt/hostpilot/webpanel/backend
python -m pytest
```

Result: `43 passed`.

```bash
cd /opt/hostpilot/webpanel/agent
python -m pytest
```

Result: `6 passed`.

```bash
cd /opt/hostpilot/webpanel/frontend
npm run build
```

Result: production build completed successfully.

## 2026-06-11 Controlled Nginx Apply Validation

Validation target:

- SSH alias: `hostpilot-lab`.
- Lab IP: `192.168.0.64`.
- Project root: `/opt/hostpilot/webpanel`.

Deployment and service validation:

- Latest local `main` tree was deployed to `/opt/hostpilot/webpanel`.
- Alembic migrations ran through `20260611_0013`.
- Core and Agent services were restarted.
- Agent remained bound to `127.0.0.1:8765`.
- Agent runs as root in the lab for the controlled Nginx apply path, with
  systemd sandboxing and allowlisted actions constraining what it can do.
- Agent service write paths were restricted to:
  `/opt/hostpilot/webpanel/agent`, `/var/www/hostpilot-sites`,
  `/etc/nginx/sites-available/hostpilot`, `/run/nginx.pid`, and
  `/var/log/nginx`.
- The lab Nginx config includes only HostPilot-managed site configs from
  `/etc/nginx/sites-available/hostpilot/*.conf`.

Web Site workflow validated:

- Created Web site record for `lab-test.local`.
- Used webroot `/var/www/hostpilot-sites/lab-test.local`.
- Generated Nginx preview.
- Generated apply plan.
- Ran dry-run.
- Ran controlled apply through Agent with typed confirmation
  `APPLY NGINX PLAN lab-test.local`.

Controlled apply result:

- Config file created only at
  `/etc/nginx/sites-available/hostpilot/lab-test.local.conf`.
- Webroot created only at `/var/www/hostpilot-sites/lab-test.local`.
- `nginx -t` passed.
- `systemctl reload nginx` returned success.
- Site record status became `applied`.
- Agent job records exist for `web.nginx.apply_site_config`.
- Audit records exist for Web apply and Agent action completion.

Safety observations:

- Initial validation attempts found missing sandbox write paths required by
  `nginx -t`; the Agent rolled back the newly written config and did not reload
  Nginx on those failed attempts.
- No unrelated Nginx site files were created or modified.
- No SSL configuration was created.
- No PHP-FPM installation or configuration was performed.

Final lab curl checks:

- Core health: HTTP `200`.
- Agent health: HTTP `200`.
- Local lab UI: HTTP `200`.
- LAN lab UI: HTTP `200`.
- Unauthenticated API proxy check: HTTP `401`, expected for a protected endpoint.

Validation commands passed locally and on the lab host:

- Backend: `70 passed`.
- Agent: `11 passed`.
- Frontend production build completed successfully.

## Current Limits

- The installer is lab-only and targets Ubuntu 26.04.
- No SSL automation is included.
- Nginx site management is limited to controlled HostPilot site config apply.
- One privileged Agent action is included for controlled Nginx site config apply.
  It remains allowlisted, loopback-only, path-constrained, and does not support
  arbitrary commands.
- Python 3.14 support remains intentionally deferred. The supported Ubuntu 26.04
  lab runtime is isolated Python 3.13 under `/opt/hostpilot/python`.

## 2026-06-16 v0.1 Lab SSH Setup Attempt

Validation target:

- SSH alias: `hostpilot-lab`.
- Lab IP: `192.168.0.64`.
- Lab UI: `http://192.168.0.64:8080`.

Result:

- Local Core health at `http://127.0.0.1:8000/health` returned HTTP `200`.
- Local frontend at `http://127.0.0.1:5173/` returned HTTP `200`.
- SSH port `192.168.0.64:22` was reachable from the Windows development
  workstation.
- Existing local key `~/.ssh/hostpilot_lab` was selected for HostPilot lab
  access.
- Password authentication succeeded for `rattes`.
- The existing public key `~/.ssh/hostpilot_lab.pub` was installed for `rattes`.
- Local SSH alias `hostpilot-lab` was updated to point at
  `rattes@192.168.0.64` with `~/.ssh/hostpilot_lab`.
- Passwordless SSH validation passed with `ssh hostpilot-lab`.
- OS/version validation returned Ubuntu 26.04 LTS.
- Sudo access exists for `rattes`; sudo prompts for the account password.

The latest v0.1 Ubuntu lab deployment and controlled Web flow were not rerun
because this task covered SSH setup only. The last completed controlled Nginx
apply validation remains the 2026-06-11 validation above.

Next lab validation should rerun:

- deploy latest `main` to `/opt/hostpilot`;
- run migrations;
- restart Core, Agent, and Nginx;
- validate Core health, Agent health, UI HTTP `200`, login, Web create/list,
  Files, Logs, Nginx preview, apply plan, dry-run, preflight, controlled apply,
  disable, re-apply, audit records, and job records.

## 2026-06-16 New Lab Deployment Validation

Validation target:

- SSH alias: `hostpilot-lab`.
- SSH user: `rattes`.
- Lab IP: `192.168.0.64`.
- Lab UI: `http://192.168.0.64:8080`.

Deployment result:

- Passwordless SSH to `hostpilot-lab` worked.
- OS/version validation returned Ubuntu 26.04 LTS.
- Sudo access exists for `rattes`; sudo prompts for the account password.
- A clean `git archive` of the current `main` commit was copied to the lab and
  extracted under `/tmp/hostpilot-src`.
- The lab installer was run from the extracted project root.
- The installer deployed HostPilot to `/opt/hostpilot/webpanel`.
- Alembic migrations ran through current head.
- Frontend production build completed on the lab.
- Core, Agent, and Nginx systemd services were installed and restarted.

Service status:

- `hostpilot-core.service`: active.
- `hostpilot-agent.service`: active.
- `nginx.service`: active.
- Core bound to `127.0.0.1:8000`.
- Agent bound to `127.0.0.1:8765`.
- Nginx exposed the lab UI on port `8080`.

Validation commands and results:

- Local backend pytest on Windows: `108 passed`.
- Local Agent pytest on Windows: `27 passed`.
- Local frontend build on Windows: passed.
- Lab backend pytest: `108 passed` with pytest cache permission warnings only.
- Lab Agent pytest: `27 passed` with pytest cache permission warnings only.
- Lab check script: `10 passed, 0 failed`.
- Core health: HTTP `200`.
- Agent health: HTTP `200`.
- Lab UI local: HTTP `200`.
- Lab UI LAN `http://192.168.0.64:8080`: HTTP `200` with HostPilot content.
- Unauthenticated API proxy check: HTTP `401`, expected for protected endpoint.
- A lab admin account was bootstrapped because the disposable lab database had
  no users.
- Lab login API returned a bearer token for the bootstrapped admin.

Not covered in this deployment validation:

- Web site create/list on the lab.
- Files/Logs on the lab.
- Nginx preview, apply plan, dry-run, preflight, controlled apply, disable, and
  re-apply on the lab.
- Audit/job validation for Web controlled actions on the lab.

## 2026-06-17 Web v0.1 Flow Validation

Validation target:

- SSH alias: `hostpilot-lab`.
- SSH user: `rattes`.
- Lab IP: `192.168.0.64`.
- Lab UI: `http://192.168.0.64:8080`.
- Install path: `/opt/hostpilot/webpanel`.

Validated Web site:

- Domain: `lab-test.local`.
- Derived webroot: `/var/www/hostpilot-sites/lab-test.local`.
- Managed Nginx config:
  `/etc/nginx/sites-available/hostpilot/lab-test.local.conf`.

Validation flow result:

- Logged in through the lab API using the bootstrapped lab admin.
- Opened the Web route through the lab UI.
- Created the `lab-test.local` Web site record.
- Confirmed `root_path` was auto-derived as
  `/var/www/hostpilot-sites/lab-test.local`; no user-entered root path was
  sent.
- Confirmed the site appeared in the Web site list.
- Confirmed row actions are available for the site workflow: Files, Logs,
  Nginx preview, plan/dry-run/apply, disable, and re-apply.
- Opened the read-only Files endpoint for the site.
- Opened the read-only Logs endpoint for the site.
- Generated the Nginx config preview.
- Marked the site ready and generated the apply plan.
- Ran the dry-run with the typed confirmation phrase; no files or commands were
  executed by the dry-run.
- Ran preflight and confirmed Agent state was `connected` with real Agent usage.
- Ran controlled apply through the Agent.
- Confirmed the Agent apply job ran `nginx -t` with return code `0`.
- Confirmed the Agent apply job ran `systemctl reload nginx` with return code
  `0`.
- Confirmed the site status became `applied`.
- Ran controlled disable through the Agent.
- Ran controlled re-apply through the Agent.
- Confirmed the final site status is `applied`.
- Confirmed job records exist for apply, disable, and re-apply.
- Confirmed audit events exist for Web and Agent actions.

Path and service validation:

- Managed config exists only at
  `/etc/nginx/sites-available/hostpilot/lab-test.local.conf`.
- No `lab-test.local.conf` file was found elsewhere under `/etc/nginx`.
- Webroot exists at `/var/www/hostpilot-sites/lab-test.local`.
- Privileged `nginx -t` returned success.
- `hostpilot-core.service`: active.
- `hostpilot-agent.service`: active.
- `nginx.service`: active.
- Core health: HTTP `200`.
- Agent health: HTTP `200`.
- Lab UI: HTTP `200`.
- Unauthenticated API proxy check: HTTP `401`, expected for protected
  endpoints.

Validation commands and results:

- Local backend pytest on Windows: `108 passed`.
- Local Agent pytest on Windows: `27 passed`.
- Local frontend build on Windows: passed.
- Lab apply job id: `3`.
- Lab disable job id: `4`.
- Lab re-apply job id: `5`.
- Web/Agent audit records found: `25`.

Notes:

- An initial manual validation command attempted `nginx -t` as the unprivileged
  `rattes` user and failed on `/run/nginx.pid` permissions. This was a manual
  validation-command issue; the Agent-controlled apply/disable/re-apply jobs ran
  `nginx -t` successfully as part of the controlled workflow.
- No product code changes were required.

## 2026-06-17 Core + Web v0.1 Final Validation Summary

Final v0.1 validation result: passed for controlled Ubuntu lab use.

- Lab IP: `192.168.0.64`.
- Core health: HTTP `200`.
- Agent health: HTTP `200`.
- UI: HTTP `200` at `http://192.168.0.64:8080`.
- Backend pytest: `108 passed`.
- Agent pytest: `27 passed`.
- Frontend build: passed.
- Web v0.1 flow: passed.

This validation confirms the controlled lab workflow only. It does not make the
release production-hardened and does not add SSL automation, PHP-FPM management,
application profiles, file write operations, or additional modules.
