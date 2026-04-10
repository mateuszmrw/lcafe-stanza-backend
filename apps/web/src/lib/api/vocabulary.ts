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
  limit = 50
): Promise<WordListResponse> {
  const params = new URLSearchParams({ language_id: String(languageId), page: String(page), limit: String(limit) })
  if (status) params.set("status", status)
  return apiClient(`/vocabulary?${params}`)
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
}): Promise<WordResponse> {
  return apiClient("/vocabulary", {
    method: "PUT",
    body: JSON.stringify(data),
  })
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
