# Module Contract

Modules extend HostPilot by registering metadata and capabilities with the Core.
The Core uses this contract to build navigation, enforce permissions, expose
routes, and route allowed agent actions.

## Registration Fields

- `slug`: Stable machine-readable identifier, such as `sites` or `nginx`.
- `name`: Human-readable module name for menus and headings.
- `version`: Module package or manifest version.
- `menuItem`: Sidebar or navigation entry definition.
- `permissions`: Permission keys owned by the module.
- `routes`: Frontend and backend route declarations.
- `agentActions`: Whitelisted agent actions the module may request.
- `dependencies`: Required Core version or other module dependencies.
- `state`: Current module state: `enabled`, `disabled`, or `locked`.

## Example Manifest Shape

```json
{
  "slug": "sites",
  "name": "Sites",
  "version": "0.1.0",
  "menuItem": {
    "label": "Sites",
    "route": "/sites"
  },
  "permissions": ["sites.read", "sites.write"],
  "routes": {
    "frontend": ["/sites"],
    "api": ["/api/modules/sites"]
  },
  "agentActions": ["sites.inspect"],
  "dependencies": {
    "core": ">=0.1.0"
  },
  "state": "locked"
}
```

## Contract Rules

Modules must not rely on arbitrary shell execution. Agent actions must be
explicitly named and whitelisted. Module API routes must declare the permissions
they require, and sensitive actions must create audit records through the Core.
