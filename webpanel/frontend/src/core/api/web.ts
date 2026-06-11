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
  provisioning_status: ProvisioningStatus;
  php_runtime: string;
  ssl_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export type ProvisioningStatus =
  | "draft"
  | "config_previewed"
  | "ready_to_apply"
  | "disabled"
  | "error";

export interface WebSiteNginxPreview {
  site_id: number;
  domain: string;
  config: string;
  saved: boolean;
}

export interface WebSiteReadinessCheck {
  slug: string;
  label: string;
  passed: boolean;
  detail: string;
}

export interface WebSiteReadiness {
  site_id: number;
  domain: string;
  provisioning_status: ProvisioningStatus;
  ready: boolean;
  checks: WebSiteReadinessCheck[];
}

export interface WebSiteNginxApplyPlan {
  site_id: number;
  domain: string;
  target_config_path: string;
  webroot_path: string;
  required_directories: string[];
  config_filename: string;
  validation_commands: string[];
  service_reload_command: string;
  risk_level: string;
  confirmation_phrase: string;
  plan_only: boolean;
}

export interface WebSiteDryRunResult {
  site_id: number;
  domain: string;
  config_content: string;
  target_config_path: string;
  webroot_path: string;
  directory_checks: string[];
  nginx_validation_command: string;
  reload_command: string;
  expected_result: string;
  executed: boolean;
  wrote_files: boolean;
}

export interface WebSiteApplyResult {
  site: WebSite;
  job_id: number;
  success: boolean;
  status: string;
  result: Record<string, unknown>;
  error: string | null;
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

export function updateWebSite(
  token: string,
  siteId: number,
  payload: {
    domain: string;
    root_path: string;
    php_runtime: string;
    ssl_enabled: boolean;
  },
) {
  return apiRequest<WebSite>(`/api/core/web/sites/${siteId}`, {
    method: "PATCH",
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

export function previewWebSiteNginxConfig(token: string, siteId: number) {
  return apiRequest<WebSiteNginxPreview>(`/api/core/web/sites/${siteId}/nginx-preview`, {
    token,
  });
}

export function getWebSiteReadiness(token: string, siteId: number) {
  return apiRequest<WebSiteReadiness>(`/api/core/web/sites/${siteId}/readiness`, {
    token,
  });
}

export function markWebSiteReadyToApply(token: string, siteId: number) {
  return apiRequest<WebSite>(`/api/core/web/sites/${siteId}/mark-ready`, {
    method: "PATCH",
    token,
  });
}

export function getWebSiteNginxApplyPlan(token: string, siteId: number) {
  return apiRequest<WebSiteNginxApplyPlan>(`/api/core/web/sites/${siteId}/nginx-apply-plan`, {
    token,
  });
}

export function runWebSiteNginxDryRun(
  token: string,
  siteId: number,
  confirmationPhrase: string,
) {
  return apiRequest<WebSiteDryRunResult>(`/api/core/web/sites/${siteId}/nginx-dry-run`, {
    method: "POST",
    token,
    body: { confirmation_phrase: confirmationPhrase },
  });
}

export function applyWebSiteNginxConfig(
  token: string,
  siteId: number,
  confirmationPhrase: string,
) {
  return apiRequest<WebSiteApplyResult>(`/api/core/web/sites/${siteId}/nginx-apply`, {
    method: "POST",
    token,
    body: { confirmation_phrase: confirmationPhrase },
  });
}
