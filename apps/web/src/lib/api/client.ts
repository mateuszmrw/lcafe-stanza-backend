import { env } from "@/src/env"
import { getAuthStore } from "@/src/stores/auth"

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly data?: unknown
  ) {
    super(message)
    this.name = "ApiError"
  }
}

function extractDetail(data: unknown): string | null {
  if (typeof data !== "object" || data === null || !("detail" in data)) return null
  const detail = (data as Record<string, unknown>).detail
  // FastAPI validation errors: array of {msg, loc, ...}
  if (Array.isArray(detail)) {
    return detail
      .map((e) => (typeof e === "object" && e !== null && "msg" in e ? String((e as Record<string, unknown>).msg) : String(e)))
      .join("; ")
  }
  return String(detail)
}

let isRefreshing = false

async function doRefresh(): Promise<string | null> {
  if (isRefreshing) return null
  isRefreshing = true
  try {
    const { refreshToken, setTokens, clearTokens } = getAuthStore()
    if (!refreshToken) {
      // Do NOT call clearTokens() here — the store may not be hydrated yet,
      // so refreshToken being null doesn't mean the user has no session.
      return null
    }
    const res = await fetch(`${env.apiUrl}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    if (!res.ok) {
      clearTokens()
      return null
    }
    const data = await res.json()
    setTokens(data.access_token, data.refresh_token)
    return data.access_token
  } finally {
    isRefreshing = false
  }
}

export async function apiClient<T = unknown>(
  path: string,
  options: RequestInit & { _retry?: boolean } = {}
): Promise<T> {
  const { accessToken } = getAuthStore()
  const { _retry, ...fetchOptions } = options

  const headers = new Headers(fetchOptions.headers)
  headers.set("Content-Type", headers.get("Content-Type") ?? "application/json")
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`)
  }

  const res = await fetch(`${env.apiUrl}${path}`, {
    ...fetchOptions,
    headers,
  })

  if (res.status === 401 && !_retry) {
    const newToken = await doRefresh()
    if (newToken) {
      return apiClient<T>(path, { ...options, _retry: true })
    }
    if (typeof window !== "undefined") {
      window.location.href = "/login"
    }
    throw new ApiError(401, "Session expired")
  }

  if (!res.ok) {
    let message = res.statusText
    let data: unknown
    try {
      data = await res.json()
      message = extractDetail(data) ?? message
    } catch {
      // ignore JSON parse error
    }
    throw new ApiError(res.status, message, data)
  }

  if (res.status === 204) return undefined as T

  return res.json() as Promise<T>
}

/** Multipart upload — skips Content-Type so browser sets boundary automatically */
export async function apiUpload<T = unknown>(
  path: string,
  formData: FormData
): Promise<T> {
  const { accessToken } = getAuthStore()

  const headers: Record<string, string> = {}
  if (accessToken) {
    headers["Authorization"] = `Bearer ${accessToken}`
  }

  const res = await fetch(`${env.apiUrl}${path}`, {
    method: "POST",
    headers,
    body: formData,
  })

  if (!res.ok) {
    let message = res.statusText
    let data: unknown
    try {
      data = await res.json()
      message = extractDetail(data) ?? message
    } catch {
      // ignore
    }
    throw new ApiError(res.status, message, data)
  }

  return res.json() as Promise<T>
}
