import { connection } from "./desktop";

export class ApiError extends Error {
  constructor(readonly status: number, readonly body: unknown) {
    super(`Request failed (${status})`);
    this.name = "ApiError";
  }
}

export async function api<T>(path: string, method = "GET", value?: unknown, signal?: AbortSignal): Promise<T> {
  const bridge = connection();
  if (!bridge?.baseUrl) throw new Error("Engine unavailable");
  const response = await fetch(bridge.baseUrl + path, {
    method, headers: { Authorization: `Bearer ${bridge.token}`, "Content-Type": "application/json" },
    ...(value === undefined ? {} : { body: JSON.stringify(value) }), signal,
  });
  if (!response.ok) {
    // Refusals carry a reason the UI has to show: a worktree needs an approval, and a
    // 409 on a stale approval id must not be reported as a generic failure.
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, body);
  }
  return response.json() as Promise<T>;
}
