# HostPilot Ubuntu Lab Deploy

This is a lab deployment template for Ubuntu Server 26.04. It is not an installer
and does not perform system changes by itself.

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
  with an isolated Python 3.13 runtime under `/opt/hostpilot/python` because the
  pinned backend dependencies do not yet install cleanly on Python 3.14.
- Root SSH was used only for the `192.168.0.63` lab validation. Production
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

## Build Backend

```bash
cd /opt/hostpilot/webpanel/backend
/opt/hostpilot/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

The Core service template binds Uvicorn to `127.0.0.1:8000`.

## Build Agent

```bash
cd /opt/hostpilot/webpanel/agent
/opt/hostpilot/python/cpython-3.13-linux-x86_64-gnu/bin/python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

The Agent template starts `python -m webpanel_agent.main` and is expected to bind
to `127.0.0.1` only. The current agent exposes only mock allowlisted actions.

## Build Frontend

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

1. Copy reviewed systemd templates into the lab systemd unit directory.
2. Copy the reviewed Nginx config into the lab Nginx configuration area.
3. Reload systemd and Nginx using your lab operating procedure.
4. Start the Agent service first.
5. Start the Core service second.
6. Open `http://<lab-host>:8080`.

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
- Lab IP: `192.168.0.63`.
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
- Nginx lab frontend: `http://192.168.0.63:8080/`.
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
- Lab IP: `192.168.0.63`.
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
- `curl http://192.168.0.63:8080/` returned HTTP `200`.
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

## Current Limits

- No installer script is provided.
- No SSL automation is included.
- No Nginx site management is included.
- No privileged Agent actions are included.
- The Agent remains limited to allowlisted mock actions.
- Python 3.14 support remains a dependency compatibility gap for Ubuntu 26.04.
