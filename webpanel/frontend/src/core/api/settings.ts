import { apiRequest } from "./client";

export interface Setting {
  key: string;
  value: string;
  is_sensitive: boolean;
}

export function listSettings(token: string) {
  return apiRequest<Setting[]>("/api/core/settings", { token });
}

export function updateSetting(token: string, key: string, value: string) {
  return apiRequest<Setting>(`/api/core/settings/${key}`, {
    method: "PATCH",
    token,
    body: { value },
  });
}
