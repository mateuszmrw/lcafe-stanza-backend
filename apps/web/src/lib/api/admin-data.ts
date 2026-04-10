import { apiClient } from "./client"

export interface DataResetResponse {
  deleted_books: number
  deleted_words: number
}

export async function resetAllData(confirmation: string): Promise<DataResetResponse> {
  return apiClient("/admin/data/reset", {
    method: "DELETE",
    body: JSON.stringify({ confirmation }),
  })
}
