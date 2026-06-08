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
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

The Core service template binds Uvicorn to `127.0.0.1:8000`.

## Build Agent

```bash
cd /opt/hostpilot/webpanel/agent
python3 -m venv .venv
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
curl http://127.0.0.1:8080/health
```

Expected exposed lab URL:

```text
http://<lab-host>:8080
```

## Current Limits

- No installer script is provided.
- No SSL automation is included.
- No Nginx site management is included.
- No privileged Agent actions are included.
- The Agent remains limited to allowlisted mock actions.
