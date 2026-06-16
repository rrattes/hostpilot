import { apiRequest } from "./client";

export type AgentAvailability = "connected" | "fallback" | "unavailable";

export interface AgentStatus {
  status: AgentAvailability;
  mode: string;
  allowed_actions: string[];
  using_real_agent: boolean;
  using_fallback: boolean;
  fallback_enabled: boolean;
  web_actions_use_real_agent: boolean;
  dev_actions_enabled: boolean;
  message: string;
}

export interface AgentActionResult {
  job_id: number;
  success: boolean;
  status: string;
  data: Record<string, unknown>;
  error: string | null;
  duration_ms: number;
}

export interface AgentJob {
  id: number;
  action: string;
  status: string;
  result: string | null;
  created_at: string;
}

export function getAgentStatus(token: string) {
  return apiRequest<AgentStatus>("/api/agent/status", { token });
}

export function executeMockAgentAction(token: string, action: string) {
  return apiRequest<AgentActionResult>(`/api/agent/actions/${action}`, {
    method: "POST",
    token,
    body: { payload: {} },
  });
}

export function listRecentAgentJobs(token: string) {
  return apiRequest<AgentJob[]>("/api/agent/jobs/recent", { token });
}
