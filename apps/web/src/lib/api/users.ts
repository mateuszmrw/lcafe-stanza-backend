import { apiClient } from "./client"

export interface ProviderInfo {
  id: string
  type: string
  slug: string
  name: string
  description: string | null
  is_builtin: boolean
  is_active: boolean
  created_at: string
}

export interface UserProfile {
  id: string
  email: string
  username: string
  role: string
  is_active: boolean
  created_at: string
  active_language_id: number | null
  active_language_code: string | null
  active_language_name: string | null
  proficiency_level: string | null
  native_language_code: string | null
  auto_ignore_proper_nouns: boolean
}

export interface ApiKeyStatus {
  provider_slug: string
  exists: boolean
}

export async function getProfile(): Promise<UserProfile> {
  return apiClient<UserProfile>("/users/me")
}

export async function updateProfile(data: {
  username?: string
  password?: string
}): Promise<UserProfile> {
  return apiClient<UserProfile>("/users/me", {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export async function getApiKeyStatus(providerSlug: string): Promise<ApiKeyStatus> {
  return apiClient<ApiKeyStatus>(`/users/me/api-keys/${providerSlug}`)
}

export async function setApiKey(providerSlug: string, apiKey: string): Promise<void> {
  await apiClient<void>(`/users/me/api-keys/${providerSlug}`, {
    method: "PUT",
    body: JSON.stringify({ api_key: apiKey }),
  })
}

export async function deleteApiKey(providerSlug: string): Promise<void> {
  await apiClient<void>(`/users/me/api-keys/${providerSlug}`, {
    method: "DELETE",
  })
}

export async function updateActiveLanguage(languageId: number): Promise<UserProfile> {
  return apiClient<UserProfile>("/users/me/active-language", {
    method: "PATCH",
    body: JSON.stringify({ language_id: languageId }),
  })
}

export async function updateProficiency(data: {
  proficiency_level?: string
  native_language_code?: string
  auto_ignore_proper_nouns?: boolean
}): Promise<UserProfile> {
  return apiClient<UserProfile>("/users/me/proficiency", {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export async function resetMyData(): Promise<{ deleted_books: number; deleted_words: number }> {
  return apiClient("/users/me/data", {
    method: "DELETE",
    body: JSON.stringify({ confirmation: "DELETE ALL DATA" }),
  })
}

export async function listMyProviders(type?: string): Promise<ProviderInfo[]> {
  const qs = type ? `?type=${type}` : ""
  return apiClient<ProviderInfo[]>(`/users/me/providers${qs}`)
}
