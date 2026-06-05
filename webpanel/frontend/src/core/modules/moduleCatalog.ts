export type ModuleState = "available" | "installed" | "enabled" | "locked";

export interface ModuleDefinition {
  slug: string;
  name: string;
  version: string;
  state: ModuleState;
  enabled: boolean;
  locked: boolean;
  installed: boolean;
}

const descriptions: Record<string, string> = {
  core: "Platform shell, registry, settings, audit, jobs, notifications, and agent gateway.",
  web: "Web management vertical entry point.",
  sites: "Website records and lifecycle workflows.",
  nginx: "Nginx configuration workflows.",
  ssl: "Certificate request and renewal workflows.",
  logs: "Operational log views and retention.",
  services: "Service inventory and controlled actions.",
  updates: "Package update visibility and policy.",
  backups: "Backup plans, jobs, and restore points.",
  "php-runtime": "PHP runtime visibility and version policy.",
  "server-system": "Host inventory and system telemetry.",
  "remote-access": "Remote access policy placeholder.",
  docker: "Container management placeholder.",
  kvm: "Virtualization management placeholder.",
};

export function moduleDescription(slug: string) {
  return descriptions[slug] ?? "Registered HostPilot module.";
}

export function moduleStatusLabel(module: ModuleDefinition) {
  if (module.state === "enabled") {
    return "Active";
  }
  if (module.state === "locked") {
    return "Locked";
  }
  return "Disabled";
}

export function moduleCardState(module: ModuleDefinition) {
  if (module.state === "enabled") {
    return "active";
  }
  if (module.state === "locked") {
    return "locked";
  }
  return "disabled";
}
