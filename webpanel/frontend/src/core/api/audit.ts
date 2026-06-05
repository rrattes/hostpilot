import { apiRequest } from "./client";

export interface AuditEvent {
  id: number;
  actor_user_id: number | null;
  action: string;
  target_type: string;
  target_id: string | null;
  outcome: string;
  metadata: string;
  created_at: string;
}

interface AuditEventList {
  items: AuditEvent[];
  total: number;
  limit: number;
  offset: number;
}

export function listAuditEvents(token: string) {
  return apiRequest<AuditEventList>("/api/core/audit/events?limit=25", { token });
}
