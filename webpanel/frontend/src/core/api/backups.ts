import { apiRequest } from "./client";

export interface CoreBackup {
  id: string;
  created_at: string;
  created_by: number | null;
  status: string;
  file_path: string;
  size_bytes: number;
}

export function listCoreBackups(token: string) {
  return apiRequest<CoreBackup[]>("/api/core/backups", { token });
}

export function createCoreBackup(token: string) {
  return apiRequest<CoreBackup>("/api/core/backups", {
    method: "POST",
    token,
  });
}
