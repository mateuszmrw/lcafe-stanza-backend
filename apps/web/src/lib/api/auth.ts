import { apiClient } from "./client"

interface TokenResponse {
  access_token: string
  refresh_token: string
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  return apiClient<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
}

export async function register(
  email: string,
  username: string,
  password: string
): Promise<TokenResponse> {
  return apiClient<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, username, password }),
  })
}

export async function refresh(refreshToken: string): Promise<TokenResponse> {
  return apiClient<TokenResponse>("/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
}

export async function logout(): Promise<void> {
  await apiClient<void>("/auth/logout", { method: "POST" })
}

export async function getSetupStatus(): Promise<{ needs_setup: boolean }> {
  return apiClient<{ needs_setup: boolean }>("/setup/status")
}

export async function setupRegister(
  email: string,
  username: string,
  password: string
): Promise<{ access_token: string; refresh_token: string }> {
  return apiClient("/setup/register", {
    method: "POST",
    body: JSON.stringify({ email, username, password }),
  })
}

export interface MeResponse {
  id: string
  email: string
  username: string
  is_admin: boolean
  is_active: boolean
}

export async function getMe(): Promise<MeResponse> {
  return apiClient<MeResponse>("/users/me")
}
