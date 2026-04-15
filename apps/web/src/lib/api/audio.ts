import { env } from "@/src/env"
import { apiClient } from "./client"
import { getAuthStore } from "@/src/stores/auth"

export interface AudioStatus {
  has_audio_overlay: boolean
  audio_overlay_status: "none" | "pending" | "in_progress" | "complete" | "failed"
  audio_duration_ms: number | null
  sentences_aligned: number
}

export interface SentenceAlignment {
  sentence_index: number
  audio_start_ms: number
  audio_end_ms: number
  audio_file: string | null
}

export async function getAlignmentsForPage(
  bookId: string,
  page: number
): Promise<SentenceAlignment[]> {
  return apiClient<SentenceAlignment[]>(`/books/${bookId}/pages/${page}/alignments`)
}

/** Returns the URL to use as <audio src>. Includes auth token as query param
 *  since <audio> elements can't set Authorization headers.
 *  For SMIL books with multiple audio files, pass filePath (storage-relative). */
export function audioStreamUrl(bookId: string, filePath?: string | null): string {
  const { accessToken } = getAuthStore()
  const url = new URL(`${env.apiUrl}/books/${bookId}/audio/stream`)
  if (accessToken) url.searchParams.set("token", accessToken)
  if (filePath) url.searchParams.set("file_path", filePath)
  return url.toString()
}

/** Returns the SSE URL for audio alignment status updates. */
export function audioStatusStreamUrl(bookId: string): string {
  const { accessToken } = getAuthStore()
  const url = new URL(`${env.apiUrl}/books/${bookId}/audio/status/stream`)
  if (accessToken) url.searchParams.set("token", accessToken)
  return url.toString()
}

/** Returns the base URL for a TTS DASH manifest (manifest.mpd).
 *  dash.js resolves segment paths relative to this URL. */
export function ttsDashManifestUrl(bookId: string, pageNumber: number): string {
  const { accessToken } = getAuthStore()
  const url = new URL(`${env.apiUrl}/books/${bookId}/tts/${pageNumber}/manifest.mpd`)
  if (accessToken) url.searchParams.set("token", accessToken)
  return url.toString()
}

/** Returns the token needed for dash.js segment request modifier. */
export function getAccessToken(): string | null {
  return getAuthStore().accessToken ?? null
}
