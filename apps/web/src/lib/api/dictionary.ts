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
  /** Source-specific extra data (e.g. accented form, aspect, examples for OpenRussian) */
  metadata?: Record<string, unknown>
}

export interface DictionaryResultGroup {
  source_dict: string
  entries: DictionaryEntry[]
}

export interface DictionaryLookupResponse {
  results: DictionaryResultGroup[]
}

export async function lookup(
  word: string,
  sourceLang: string,
  targetLang: string,
  dicts?: string   // comma-separated slugs filter, e.g. "wiktionary,openrussian"
): Promise<DictionaryLookupResponse> {
  const params = new URLSearchParams({ word, source_lang: sourceLang, target_lang: targetLang })
  if (dicts) params.set("dicts", dicts)
  return apiClient<DictionaryLookupResponse>(`/dictionary?${params}`)
}
