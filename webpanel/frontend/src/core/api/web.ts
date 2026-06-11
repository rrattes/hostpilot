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

export interface WebSite {
  id: number;
  domain: string;
  root_path: string;
  status: string;
  php_runtime: string;
  ssl_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export function getWebStatus(token: string) {
  return apiRequest<WebStatus>("/api/core/web/status", { token });
}

export function listWebSites(token: string) {
  return apiRequest<WebSite[]>("/api/core/web/sites", { token });
}

export function createWebSite(
  token: string,
  payload: {
    domain: string;
    root_path: string;
    php_runtime: string;
    ssl_enabled: boolean;
  },
) {
  return apiRequest<WebSite>("/api/core/web/sites", {
    method: "POST",
    token,
    body: payload,
  });
}

export function disableWebSite(token: string, siteId: number) {
  return apiRequest<WebSite>(`/api/core/web/sites/${siteId}/disable`, {
    method: "PATCH",
    token,
  });
}
