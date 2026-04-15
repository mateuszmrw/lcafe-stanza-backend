import { apiClient } from "./client"

export interface WebsitePreview {
  url: string
  title: string
  excerpt: string
  word_count: number
  author: string | null
}

export interface WebsiteImportResponse {
  id: string
  title: string
  status: string
  language_id: number
}

export async function previewWebsite(url: string): Promise<WebsitePreview> {
  return apiClient("/website/preview", {
    method: "POST",
    body: JSON.stringify({ url }),
  })
}

export async function importWebsite(params: {
  url: string
  title: string
  language_id: number
}): Promise<WebsiteImportResponse> {
  return apiClient("/website/import", {
    method: "POST",
    body: JSON.stringify(params),
  })
}
