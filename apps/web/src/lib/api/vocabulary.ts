import { env } from "@/src/env"
import { getAuthStore } from "@/src/stores/auth"
import { apiClient } from "./client"

export interface WordResponse {
  id: string
  word: string
  lemma: string
  pos: string
  reading: string
  status: string
  hint: string | null
  language_id: number
  lookup_count: number
  exposure_count: number
  difficulty_score: number | null
  created_at: string
}

export interface WordListResponse {
  items: WordResponse[]
  total: number
  page: number
  limit: number
}

export async function listVocabulary(
  languageId: number,
  status?: string,
  page = 1,
  limit = 50,
  pos?: string,
  search?: string,
): Promise<WordListResponse> {
  const params = new URLSearchParams({ language_id: String(languageId), page: String(page), limit: String(limit) })
  if (status) params.set("status", status)
  if (pos) params.set("pos", pos)
  if (search) params.set("search", search)
  return apiClient(`/vocabulary?${params}`)
}

export async function bulkUpdateStatus(ids: string[], status: string): Promise<void> {
  await apiClient<void>("/vocabulary/bulk", {
    method: "PATCH",
    body: JSON.stringify({ ids, status }),
  })
}

export async function updateWordStatus(
  wordId: string,
  status: string
): Promise<WordResponse> {
  return apiClient(`/vocabulary/${wordId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  })
}

export async function upsertWordStatus(data: {
  word: string
  status: string
  language_id: number
  lemma?: string
  pos?: string
  reading?: string
  gender?: string
  feats?: string
  hint?: string | null
  sentence_context?: string | null
}): Promise<WordResponse> {
  return apiClient("/vocabulary", {
    method: "PUT",
    body: JSON.stringify(data),
  })
}

export async function downloadVocabularyCSV(languageId: number, filename = "vocabulary.csv"): Promise<void> {
  const { accessToken } = getAuthStore()
  const res = await fetch(`${env.apiUrl}/vocabulary/export?language_id=${languageId}`, {
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
  })
  if (!res.ok) throw new Error("Export failed")
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}


export async function batchUpsertWordStatus(
  items: Array<{
    word: string
    status: string
    language_id: number
    lemma?: string
    pos?: string
    reading?: string
    gender?: string
    feats?: string
  }>
): Promise<void> {
  return apiClient("/vocabulary/batch", {
    method: "POST",
    body: JSON.stringify(items),
  })
}

export async function recordExposures(
  lemmas: string[],
  languageId: number
): Promise<void> {
  if (!lemmas.length) return
  return apiClient("/vocabulary/record-exposures", {
    method: "POST",
    body: JSON.stringify({ lemmas, language_id: languageId }),
  })
}
