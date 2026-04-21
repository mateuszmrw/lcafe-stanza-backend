import { apiClient } from "./client"
import type { ReaderConfig } from "./languages"

export interface UserAdminResponse {
  id: string
  email: string
  username: string
  role: string
  is_active: boolean
  created_at: string
  proficiency_level: string | null
  native_language_code: string | null
}

export interface ProviderAdminResponse {
  id: string
  type: string
  slug: string
  name: string
  description: string | null
  is_builtin: boolean
  is_active: boolean
  created_at: string
}

export interface LanguageAdminResponse {
  id: number
  code: string
  name: string
  flag_emoji: string | null
  is_active: boolean
  reader_config: Record<string, boolean>
}

export async function listAdminUsers(
  page = 1,
  limit = 50
): Promise<UserAdminResponse[]> {
  return apiClient<UserAdminResponse[]>(`/admin/users?page=${page}&limit=${limit}`)
}

export async function updateAdminUser(
  userId: string,
  data: {
    role?: string
    is_active?: boolean
    password?: string
    proficiency_level?: string
    native_language_code?: string
  }
): Promise<UserAdminResponse> {
  return apiClient<UserAdminResponse>(`/admin/users/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export async function createAdminUser(data: {
  email: string
  username: string
  password: string
  role?: string
  proficiency_level?: string
  native_language_code?: string
}): Promise<UserAdminResponse> {
  return apiClient<UserAdminResponse>("/admin/users", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function deleteAdminUser(userId: string): Promise<void> {
  await apiClient<void>(`/admin/users/${userId}`, { method: "DELETE" })
}

export async function listAdminProviders(
  type?: string
): Promise<ProviderAdminResponse[]> {
  const qs = type ? `?type=${type}` : ""
  return apiClient<ProviderAdminResponse[]>(`/admin/providers${qs}`)
}

export async function updateAdminProvider(
  providerId: string,
  data: { name?: string; description?: string; is_active?: boolean }
): Promise<ProviderAdminResponse> {
  return apiClient<ProviderAdminResponse>(`/admin/providers/${providerId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  })
}

export async function listAdminLanguages(): Promise<LanguageAdminResponse[]> {
  return apiClient<LanguageAdminResponse[]>("/admin/languages")
}

export interface DictionaryStats {
  source_lang: string
  target_lang: string
  entry_count: number
}

export interface DictionaryUploadResult {
  source_lang: string
  target_lang: string
  source_dict: string
  inserted: number
  deleted: number
}

export interface DictionarySourceResponse {
  slug: string
  name: string
  description: string | null
  supported_pairs: { source_lang: string; target_lang: string }[]
  priority: number
  is_active: boolean
  entry_count: number
}

export interface DictionarySourceUpdate {
  name?: string
  description?: string
  priority?: number
  is_active?: boolean
}

export async function getDictionaryStats(): Promise<DictionaryStats[]> {
  return apiClient<DictionaryStats[]>("/admin/dictionary/stats")
}

export async function getDictionarySources(): Promise<DictionarySourceResponse[]> {
  return apiClient<DictionarySourceResponse[]>("/admin/dictionary/sources")
}

export async function updateDictionarySource(
  slug: string,
  update: DictionarySourceUpdate
): Promise<DictionarySourceResponse> {
  return apiClient<DictionarySourceResponse>(`/admin/dictionary/sources/${slug}`, {
    method: "PATCH",
    body: JSON.stringify(update),
    headers: { "Content-Type": "application/json" },
  })
}

export async function deleteDictionarySource(slug: string): Promise<void> {
  await apiClient<void>(`/admin/dictionary/sources/${slug}`, { method: "DELETE" })
}

export async function uploadDictionary(
  sourceLang: string,
  targetLang: string,
  file: File,
  replace = true,
  sourceSlug = "wiktionary"
): Promise<DictionaryUploadResult> {
  const form = new FormData()
  form.append("file", file)
  const { accessToken } = (await import("@/src/stores/auth")).getAuthStore()
  const { env } = await import("@/src/env")
  const params = new URLSearchParams({ replace: String(replace), source_slug: sourceSlug })
  const res = await fetch(
    `${env.apiUrl}/admin/dictionary/upload/${sourceLang}/${targetLang}?${params}`,
    {
      method: "POST",
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      body: form,
    }
  )
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error((data as { detail?: string }).detail ?? res.statusText)
  }
  return res.json()
}

export async function deleteDictionaryPair(
  sourceLang: string,
  targetLang: string
): Promise<DictionaryUploadResult> {
  return apiClient<DictionaryUploadResult>(`/admin/dictionary/${sourceLang}/${targetLang}`, {
    method: "DELETE",
  })
}

export interface FrequencyLanguageStat {
  language_code: string
  entry_count: number
}

export interface FrequencyImportResult {
  language_code: string
  inserted: number
  deleted: number
}

export async function listFrequencyStats(): Promise<FrequencyLanguageStat[]> {
  return apiClient<FrequencyLanguageStat[]>("/admin/frequencies/stats")
}

export async function uploadFrequencies(
  languageCode: string,
  file: File,
  replace = true
): Promise<FrequencyImportResult> {
  const form = new FormData()
  form.append("file", file)
  const { accessToken } = (await import("@/src/stores/auth")).getAuthStore()
  const { env } = await import("@/src/env")
  const res = await fetch(
    `${env.apiUrl}/admin/frequencies/upload/${languageCode}?replace=${replace}`,
    {
      method: "POST",
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      body: form,
    }
  )
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error((data as { detail?: string }).detail ?? res.statusText)
  }
  return res.json()
}

export async function deleteFrequencies(languageCode: string): Promise<FrequencyImportResult> {
  return apiClient<FrequencyImportResult>(`/admin/frequencies/${languageCode}`, {
    method: "DELETE",
  })
}

export interface SystemKeyStatus {
  provider_slug: string
  provider: ProviderAdminResponse
  exists: boolean
  source: "database" | "env" | "none"
}

export async function getSystemKeys(): Promise<SystemKeyStatus[]> {
  return apiClient<SystemKeyStatus[]>("/admin/system/api-keys")
}

export async function setSystemKey(providerSlug: string, apiKey: string): Promise<void> {
  await apiClient<void>(`/admin/system/api-keys/${providerSlug}`, {
    method: "PUT",
    body: JSON.stringify({ api_key: apiKey }),
  })
}

export async function deleteSystemKey(providerSlug: string): Promise<void> {
  await apiClient<void>(`/admin/system/api-keys/${providerSlug}`, {
    method: "DELETE",
  })
}

export interface NlpConfigResponse {
  language_id: number
  provider_id: string
  config: Record<string, unknown>
}

export async function getNlpConfig(languageId: number): Promise<NlpConfigResponse> {
  return apiClient<NlpConfigResponse>(`/admin/languages/${languageId}/nlp-config`)
}

export async function setNlpConfig(
  languageId: number,
  providerId: string,
  config: Record<string, unknown>
): Promise<NlpConfigResponse> {
  return apiClient<NlpConfigResponse>(`/admin/languages/${languageId}/nlp-config`, {
    method: "PUT",
    body: JSON.stringify({ provider_id: providerId, config }),
  })
}

export interface LLMProviderStatus {
  provider_slug: string
  provider: ProviderAdminResponse
  key_source: "database" | "env" | "none"
  model: string | null
  model_source: "database" | "env"
}

export async function getLLMConfig(): Promise<LLMProviderStatus[]> {
  return apiClient<LLMProviderStatus[]>("/admin/llm")
}

export async function setLLMConfig(
  providerSlug: string,
  data: { api_key?: string; model?: string }
): Promise<void> {
  await apiClient<void>(`/admin/llm/${providerSlug}`, {
    method: "PUT",
    body: JSON.stringify(data),
  })
}

export async function deleteLLMConfig(providerSlug: string): Promise<void> {
  await apiClient<void>(`/admin/llm/${providerSlug}`, {
    method: "DELETE",
  })
}

export async function updateAdminLanguage(
  languageId: number,
  data: { name?: string; flag_emoji?: string; is_active?: boolean }
): Promise<LanguageAdminResponse> {
  return apiClient<LanguageAdminResponse>(`/admin/languages/${languageId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  })
}

export async function setReaderConfig(
  languageId: number,
  readerConfig: ReaderConfig
): Promise<LanguageAdminResponse> {
  return apiClient<LanguageAdminResponse>(`/admin/languages/${languageId}/reader-config`, {
    method: "PUT",
    body: JSON.stringify({ reader_config: readerConfig }),
  })
}

export interface RetokenizeResult {
  enqueued: number
}

export async function retokenizeAll(languageId?: number): Promise<RetokenizeResult> {
  const qs = languageId !== undefined ? `?language_id=${languageId}` : ""
  return apiClient<RetokenizeResult>(`/admin/stanza/retokenize${qs}`, { method: "POST" })
}

export interface CognateStatusResponse {
  row_count: number
  last_imported_at: string | null
  pairs: Array<{ l2: string; l1_codes: string[] }>
}

export interface CognateUploadResponse {
  enqueued: boolean
  filename: string
}

export async function getCognateStatus(): Promise<CognateStatusResponse> {
  return apiClient<CognateStatusResponse>("/admin/cognates/status")
}

export async function uploadCognates(file: File): Promise<CognateUploadResponse> {
  const form = new FormData()
  form.append("file", file)
  const { accessToken } = (await import("@/src/stores/auth")).getAuthStore()
  const { env } = await import("@/src/env")
  const res = await fetch(`${env.apiUrl}/admin/cognates/upload`, {
    method: "POST",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
    body: form,
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error((data as { detail?: string }).detail ?? res.statusText)
  }
  return res.json()
}
