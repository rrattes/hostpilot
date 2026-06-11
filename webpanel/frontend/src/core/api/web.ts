import { apiRequest } from "./client";

export type WebSectionStatusValue = "unavailable" | "coming_soon";

export interface WebSectionStatus {
  slug: string;
  name: string;
  status: WebSectionStatusValue;
  description: string;
  action_label: string;
  action_available: boolean;
}

export interface WebStatus {
  module_slug: string;
  module_state: string;
  enabled: boolean;
  operational: boolean;
  sections: WebSectionStatus[];
}

export function getWebStatus(token: string) {
  return apiRequest<WebStatus>("/api/core/web/status", { token });
}
