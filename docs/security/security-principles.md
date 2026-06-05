# Security Principles

Security boundaries are part of the platform foundation, even while this first
scaffold uses mock data.

## No Arbitrary Shell Execution

The Core never executes arbitrary shell commands. It must not include terminal,
remote shell, generic command runner, or raw command execution features.

## Whitelisted Agent Actions

The agent must only expose whitelisted actions. Future modules may register
allowed actions, but every action must have a typed contract, validation, and an
authorization path through the Core.

## API-Enforced RBAC

RBAC must be enforced in backend APIs, not only in the frontend. Frontend checks
may improve usability, but they are not a security boundary.

## Audit Sensitive Actions

Every sensitive action must create an audit log record. Audit records should
include the actor, target, action, time, result, and relevant request context.

## Module-Owned Permissions

Modules define their own permissions and agent actions. The Core stores and
enforces registration metadata, while modules remain responsible for declaring
the permissions required by each route and action.

## Safe Confirmations

Destructive or sensitive future actions must require explicit confirmation
through a Core confirmation boundary before execution.
