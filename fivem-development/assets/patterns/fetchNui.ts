/** NUI helper for TypeScript frontends (React/Vite or plain TS). */
export type NuiResponse<T> = { ok: boolean; code?: string; data?: T };

declare function GetParentResourceName(): string;

export async function fetchNui<T = unknown>(
  action: string,
  payload: unknown = {},
  timeoutMs = 6000,
): Promise<NuiResponse<T>> {
  if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(action)) return { ok: false, code: 'invalid_action' };

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`https://${GetParentResourceName()}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json; charset=UTF-8' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    // Blocked cross-resource calls (strict mode) and missing callbacks come back as non-OK.
    if (!res.ok) return { ok: false, code: `http_${res.status}` };
    const body: unknown = await res.json();
    if (typeof body !== 'object' || body === null || !('ok' in body)) {
      return { ok: false, code: 'bad_response' };
    }
    return body as NuiResponse<T>;
  } catch {
    return { ok: false, code: 'network_or_timeout' };
  } finally {
    clearTimeout(timer);
  }
}
