import { apiRequest } from "./client";

export interface Job {
  id: number;
  type: string;
  module: string;
  action: string;
  status: string;
  payload: string;
  result: string | null;
  created_at: string;
  updated_at: string;
}

interface JobList {
  items: Job[];
  total: number;
  limit: number;
  offset: number;
}

export function listJobs(token: string) {
  return apiRequest<JobList>("/api/core/jobs?limit=25", { token });
}

export function createMockJob(token: string) {
  return apiRequest<Job>("/api/core/jobs/mock", {
    method: "POST",
    token,
    body: { module: "core", action: "mock.dev", payload: "{\"source\":\"frontend\"}" },
  });
}
