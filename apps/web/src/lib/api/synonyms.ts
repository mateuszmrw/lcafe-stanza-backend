import { apiClient } from "./client"

export interface SynonymEntry {
  word: string
  register: string
  nuance: string
  example: string | null
}

export interface SynonymNuanceResponse {
  synonyms: SynonymEntry[]
  native_language_code: string
}

export async function getSynonymNuance(params: {
  language_id: number
  language_code: string
  word: string
  pos: string
  lemma: string
  context_sentence?: string
}): Promise<SynonymNuanceResponse> {
  return apiClient<SynonymNuanceResponse>("/synonyms/nuance", {
    method: "POST",
    body: JSON.stringify(params),
  })
}
