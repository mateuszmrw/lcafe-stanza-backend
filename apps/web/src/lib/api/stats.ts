import { apiClient } from "./client"

export interface StatsResponse {
  language_code: string
  word_counts: Record<string, number>
  known_over_time: { date: string; known_cumulative: number }[]
  frequency_coverage: { top_1k: number | null; top_5k: number | null; top_10k: number | null }
  books_total: number
  pages_read: number
}

export async function getStats(languageCode: string): Promise<StatsResponse> {
  return apiClient<StatsResponse>(`/stats/${languageCode}`)
}
