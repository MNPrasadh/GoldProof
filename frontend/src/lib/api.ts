const TOKEN_KEY = "goldproof_access_token";

export function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit & { skipAuth?: boolean } = {}
): Promise<T> {
  const { skipAuth, headers, ...rest } = options;
  const token = skipAuth ? null : getStoredToken();

  const mergedHeaders = new Headers(headers || {});
  if (!(rest.body instanceof FormData) && !mergedHeaders.has("Content-Type")) {
    mergedHeaders.set("Content-Type", "application/json");
  }
  if (token) {
    mergedHeaders.set("Authorization", `Bearer ${token}`);
  }

  const resp = await fetch(`${getApiBaseUrl()}${path}`, {
    ...rest,
    headers: mergedHeaders,
  });

  if (!resp.ok) {
    let message = `Request failed (${resp.status})`;
    try {
      const errJson = await resp.json();
      if (typeof errJson?.detail === "string") {
        message = errJson.detail;
      } else if (Array.isArray(errJson?.detail)) {
        message = errJson.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ");
      }
    } catch {
      // ignore non-json body
    }
    throw new ApiError(message, resp.status);
  }

  return (await resp.json()) as T;
}
