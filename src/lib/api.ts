import { connection } from "./desktop";

export async function api<T>(path: string, method = "GET", value?: unknown, signal?: AbortSignal): Promise<T> {
  const bridge = connection();
  if (!bridge?.baseUrl) throw new Error("Engine unavailable");
  const response = await fetch(bridge.baseUrl + path, {
    method, headers: { Authorization: `Bearer ${bridge.token}`, "Content-Type": "application/json" },
    ...(value === undefined ? {} : { body: JSON.stringify(value) }), signal,
  });
  if (!response.ok) throw new Error("Request unavailable");
  return response.json() as Promise<T>;
}
