import { apiRequest } from "./client";
import type { AgentAvailability } from "./agent";

export interface LocalServerStatus {
  slug: string;
  name: string;
  description: string;
  hostname: string;
  os_name: string;
  is_local: boolean;
}

export interface CoreHealthStatus {
  product: string;
  core_version: string;
  core_status: "ok";
  database_status: "ok" | "error";
  agent_status: AgentAvailability;
  runtime: string;
  database: string;
  agent_mode: string;
  agent_web_actions_use_real_agent: boolean;
  local_server: LocalServerStatus | null;
  enabled_modules_count: number;
  locked_modules_count: number;
  recent_jobs_count: number;
  recent_audit_events_count: number;
  generated_at: string;
}

export function getCoreStatus(token: string) {
  return apiRequest<CoreHealthStatus>("/api/core/status", { token });
}
