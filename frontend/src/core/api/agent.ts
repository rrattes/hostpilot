import { apiRequest } from "./client";

export interface AgentStatus {
  status: string;
  mode: string;
  allowed_actions: string[];
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
