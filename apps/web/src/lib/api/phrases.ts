import { apiClient } from "./client"

export interface PhraseResponse {
  id: string
  language_id: number | null
  text: string
  translation: string | null
  context: string | null
  book_id: string | null
  page: number | null
  status: "learning" | "known"
  created_at: string
}

export interface PhraseListResponse {
  items: PhraseResponse[]
  total: number
  page: number
  limit: number
}

export interface PhraseCreate {
  language_id?: number | null
  text: string
  translation?: string | null
  context?: string | null
  book_id?: string | null
  page?: number | null
}

export async function createPhrase(data: PhraseCreate): Promise<PhraseResponse> {
  return apiClient<PhraseResponse>("/phrases", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function listPhrases(
  languageId?: number,
  status?: string,
  page = 1,
  limit = 50
): Promise<PhraseListResponse> {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) })
  if (languageId != null) params.set("language_id", String(languageId))
  if (status) params.set("status", status)
  return apiClient<PhraseListResponse>(`/phrases?${params}`)
}

export async function updatePhraseStatus(id: string, status: string): Promise<PhraseResponse> {
  return apiClient<PhraseResponse>(`/phrases/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  })
}

export async function deletePhrase(id: string): Promise<void> {
  await apiClient<void>(`/phrases/${id}`, { method: "DELETE" })
}
