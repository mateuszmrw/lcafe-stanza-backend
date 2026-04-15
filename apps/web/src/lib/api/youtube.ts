import { apiClient } from "./client"

export interface AvailableSubtitle {
  lang_code: string
  label: string
  is_auto: boolean
}

export interface YouTubePreview {
  video_id: string
  title: string
  duration_ms: number | null
  channel_name: string | null
  thumbnail_url: string | null
  available_subtitles: AvailableSubtitle[]
}

export interface YouTubeImportResponse {
  video_id: string
  content_item_id: string
  status: string
}

export async function previewYouTube(url: string): Promise<YouTubePreview> {
  return apiClient(`/youtube/preview?url=${encodeURIComponent(url)}`)
}

export async function importYouTube(opts: {
  url: string
  title: string
  language_id: number
  subtitle_lang_code: string
  use_auto_captions: boolean
}): Promise<YouTubeImportResponse> {
  return apiClient("/youtube/import", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(opts),
  })
}
