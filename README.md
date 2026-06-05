# HostPilot

HostPilot is a modular local server management platform. The Core is neutral,
small, and deliberately unaware of any specific infrastructure vertical. Product
capabilities are added by installed modules.

The first target vertical is Web Server Management, but this repository is only
the Core foundation scaffold. Web, Sites, Nginx, SSL, Docker, KVM, firewall,
updates, PHP, and related capabilities are future modules and are not implemented
in the Core.

## Architecture

- Backend Core: Python FastAPI.
- Database: SQLite to start, with SQLAlchemy and Alembic planned for ORM and
  migrations.
- Frontend: React, Vite, and TypeScript. Production serves static built files
  through Nginx and does not require a Node.js runtime.
- Agent: Python local agent package with a safe mock implementation for now.
- Deployment target: Ubuntu Server 26.04 LTS.
- Secondary compatibility: Ubuntu Server 24.04 LTS where simple.

## Core Responsibilities

The Core owns generic platform capabilities:

- Auth boundary.
- RBAC boundary.
- Module registry.
- Settings.
- Jobs.
- Audit log.
- Notifications.
- Agent gateway.
- UI shell.
- Local server record.
- Safe confirmations for sensitive future actions.

## Current Non-Goals

This scaffold intentionally does not implement real login, real RBAC, an
installer, SSL, PHP, Docker, KVM, terminal access, remote shell access, SSH,
Guacamole, RDP, VNC, package updates, service control, or real Nginx changes.

The Core does not execute shell commands and does not expose arbitrary command
execution.

## Development

### Backend

```bash
cd webpanel/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/health` or
`http://127.0.0.1:8000/api/core/status`.

### Frontend

```bash
cd webpanel/frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

### Agent Mock

```bash
cd webpanel/agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m webpanel_agent.main
```

The agent mock returns static health and system information and performs no real
system actions.
