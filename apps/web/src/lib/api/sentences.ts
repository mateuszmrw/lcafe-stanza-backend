import { apiClient } from "./client"

export interface SavedSentence {
  id: string
  language_id: number
  sentence_text: string
  sentence_index: number
  book_id: string | null
  created_at: string
}

export async function saveSentence(data: {
  language_id: number
  sentence_text: string
  sentence_index: number
  book_id?: string
}): Promise<SavedSentence> {
  return apiClient("/sentences", {
    method: "POST",
    body: JSON.stringify(data),
  })
}

export async function listSentences(languageId: number): Promise<SavedSentence[]> {
  return apiClient(`/sentences?language_id=${languageId}`)
}

export async function deleteSentence(sentenceId: string): Promise<void> {
  return apiClient(`/sentences/${sentenceId}`, { method: "DELETE" })
}
