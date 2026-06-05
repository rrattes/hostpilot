# Core Platform

The HostPilot Core is the stable platform layer beneath all product verticals. It
provides generic management primitives and a UI shell, but it does not know how
to manage web servers, certificates, package updates, containers, virtualization,
or host firewall rules.

## Design Intent

The Core should stay neutral. Installed modules define the product surface by
registering their navigation, permissions, API routes, UI routes, and allowed
agent actions.

This keeps the platform extensible while preventing infrastructure-specific
behavior from leaking into shared code.

## Core Capabilities

- Authentication and user boundary.
- RBAC enforcement boundary.
- Module registry and module state.
- Settings storage.
- Background job records.
- Audit log records.
- Notifications.
- Agent gateway.
- Local server record.
- Safe confirmation workflow boundary.
- Shared frontend layout and route shell.

## Module-Owned Capabilities

Modules will own vertical behavior such as Sites, Nginx, SSL, PHP Runtime,
Services, Updates, Backups, Docker / Containers, and KVM / Virtualization.

Those modules must define their own permissions, API behavior, UI routes, and
agent actions. The Core may store and expose the registration metadata, but it
must not implement their operational logic.

## Runtime Model

In production, the frontend is built into static files and served by Nginx. Node.js
is a development and build tool only. The backend Core and local agent run as
Python services.
