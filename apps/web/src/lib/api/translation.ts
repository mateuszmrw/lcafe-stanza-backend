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

export interface TranslationAvailabilityResponse {
  available: boolean
  providers: ProviderInfo[]
}

export interface TranslationResult {
  provider_slug: string
  target_lang: string
  translated_texts: string[]
}

export interface TranslationResponse {
  results: TranslationResult[]
}

export async function getTranslationAvailable(): Promise<TranslationAvailabilityResponse> {
  return apiClient<TranslationAvailabilityResponse>("/translate/available")
}

export async function translate(
  text: string,
  sourceLang: string
): Promise<TranslationResponse> {
  return apiClient<TranslationResponse>("/translate", {
    method: "POST",
    body: JSON.stringify({ text, source_lang: sourceLang }),
  })
}
