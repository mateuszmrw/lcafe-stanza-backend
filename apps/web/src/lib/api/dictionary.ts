import { apiClient } from "./client"

export interface FrequencyInfo {
  rank: number
  tier: "very_common" | "common" | "uncommon" | "rare" | "very_rare"
}

export interface WordForm {
  form: string
  tags: string[]
}

export interface DictionaryEntry {
  lemma: string
  pos: string
  glosses: string[]
  forms: WordForm[]
  etymology: string | null
  labels: string[]
  frequency: FrequencyInfo | null
}

export interface DictionaryProviderResult {
  provider_slug: string
  entries: DictionaryEntry[]
}

export interface DictionaryLookupResponse {
  results: DictionaryProviderResult[]
}

export async function lookup(
  word: string,
  sourceLang: string,
  targetLang: string,
  providerSlug?: string
): Promise<DictionaryLookupResponse> {
  const params = new URLSearchParams({ word, source_lang: sourceLang, target_lang: targetLang })
  if (providerSlug) params.set("provider_slug", providerSlug)
  return apiClient<DictionaryLookupResponse>(`/dictionary?${params}`)
}
