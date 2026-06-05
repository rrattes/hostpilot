import { apiRequest } from "./client";

export interface LocalServer {
  slug: string;
  name: string;
  description: string;
  hostname: string;
  os_name: string;
  is_local: boolean;
}

export function getLocalServer(token: string) {
  return apiRequest<LocalServer>("/api/core/server/local", { token });
}

export function updateLocalServer(token: string, name: string, description: string) {
  return apiRequest<LocalServer>("/api/core/server/local", {
    method: "PATCH",
    token,
    body: { name, description },
  });
}
