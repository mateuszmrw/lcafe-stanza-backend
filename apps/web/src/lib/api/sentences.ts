import { apiClient } from "./client"

export interface SentenceTokenData {
  w: string
  pos: string
  feats: string
  dep_head: number
  dep_rel: string
}

export interface SavedSentence {
  id: string
  language_id: number
  sentence_text: string
  sentence_index: number
  book_id: string | null
  tokens: SentenceTokenData[] | null
  created_at: string
}

export async function saveSentence(data: {
  language_id: number
  sentence_text: string
  sentence_index: number
  book_id?: string
  tokens?: SentenceTokenData[]
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
