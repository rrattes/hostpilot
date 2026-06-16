export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

type ApiErrorPayload = {
  detail?: unknown;
  error?: unknown;
  message?: unknown;
};

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH";
  token?: string | null;
  body?: unknown;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers({ Accept: "application/json" });

  if (options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (options.token) {
    headers.set("Authorization", `Bearer ${options.token}`);
  }

  const response = await fetch(path, {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  if (!response.ok) {
    const fallback = response.status === 401 ? "Invalid credentials." : "Request failed.";
    const message = await readErrorMessage(response, fallback);
    if (response.status === 401 && options.token && typeof window !== "undefined") {
      window.dispatchEvent(new Event("hostpilot:auth-expired"));
    }
    throw new ApiError(message, response.status);
  }

  return response.json() as Promise<T>;
}

async function readErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const raw = await response.text();
    if (!raw.trim()) return fallback;
    try {
      const payload = JSON.parse(raw) as ApiErrorPayload;
      return normalizeApiErrorPayload(payload) ?? fallback;
    } catch {
      return raw.trim();
    }
  } catch {
    return fallback;
  }
}

export function apiErrorMessage(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function normalizeApiErrorPayload(payload: unknown): string | null {
  if (payload === null || payload === undefined) return null;
  if (typeof payload === "string") return payload.trim() || null;
  if (Array.isArray(payload)) return normalizeApiErrorList(payload);
  if (typeof payload !== "object") return String(payload);

  const record = payload as Record<string, unknown>;
  if ("detail" in record) return normalizeApiErrorPayload(record.detail);
  if ("message" in record) return normalizeApiErrorPayload(record.message);
  if ("error" in record) return normalizeApiErrorPayload(record.error);

  const validationMessage = normalizeValidationIssue(record);
  if (validationMessage) return validationMessage;

  const parts = Object.entries(record)
    .map(([key, value]) => {
      const normalized = normalizeApiErrorPayload(value);
      return normalized ? `${humanizeKey(key)}: ${normalized}` : null;
    })
    .filter((item): item is string => item !== null);
  return parts.length > 0 ? parts.join("; ") : null;
}

function normalizeApiErrorList(items: unknown[]): string | null {
  const parts = items
    .map((item) => normalizeApiErrorPayload(item))
    .filter((item): item is string => item !== null);
  return parts.length > 0 ? parts.join("; ") : null;
}

function normalizeValidationIssue(record: Record<string, unknown>): string | null {
  const message = typeof record.msg === "string"
    ? record.msg
    : typeof record.message === "string"
      ? record.message
      : null;
  if (!message) return null;

  const location = Array.isArray(record.loc)
    ? record.loc
        .filter((part) => part !== "body" && part !== "query" && part !== "path")
        .map((part) => String(part))
        .join(".")
    : "";
  return location ? `${humanizeKey(location)}: ${message}` : message;
}

function humanizeKey(value: string): string {
  return value.replace(/_/g, " ");
}
