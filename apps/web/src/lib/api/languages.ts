import { apiClient } from "./client"

export interface Language {
  id: number
  code: string
  name: string
  flag_emoji: string | null
}

export async function listLanguages(): Promise<Language[]> {
  return apiClient("/languages")
}
