import { apiClient } from "./client"

export interface AnkiSyncResponse {
  synced: number
  queued: number
  pending_total: number
}

export interface AnkiSettingsResponse {
  anki_connect_url: string | null
  updated_at: string
}

export async function syncToAnki(languageId: number): Promise<AnkiSyncResponse> {
  return apiClient("/vocabulary/sync-anki", {
    method: "POST",
    body: JSON.stringify({ language_id: languageId }),
  })
}

export async function getAnkiStatus(languageId: number): Promise<AnkiSyncResponse> {
  return apiClient(`/vocabulary/anki-status?language_id=${languageId}`)
}

export async function getAnkiSettings(): Promise<AnkiSettingsResponse> {
  return apiClient("/admin/anki/settings")
}

export async function updateAnkiSettings(url: string | null): Promise<AnkiSettingsResponse> {
  return apiClient("/admin/anki/settings", {
    method: "PATCH",
    body: JSON.stringify({ anki_connect_url: url }),
  })
}

export async function testAnkiConnection(): Promise<{ success: boolean; message: string }> {
  return apiClient("/admin/anki/test", { method: "POST" })
}
