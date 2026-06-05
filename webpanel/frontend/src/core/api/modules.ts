import { apiRequest } from "./client";
import type { ModuleDefinition, ModuleState } from "../modules/moduleCatalog";

export function listModules(token: string) {
  return apiRequest<ModuleDefinition[]>("/api/core/modules", { token });
}

export function updateModuleState(token: string, slug: string, state: ModuleState) {
  return apiRequest<ModuleDefinition>(`/api/core/modules/${slug}`, {
    method: "PATCH",
    token,
    body: { state },
  });
}
