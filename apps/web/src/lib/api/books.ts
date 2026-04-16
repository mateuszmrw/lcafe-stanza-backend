import { env } from "@/src/env"
import { getAuthStore } from "@/src/stores/auth"
import { apiClient, apiUpload } from "./client"

export interface BookListItem {
  id: string
  title: string
  description: string | null
  status: "pending" | "processing" | "completed" | "failed"
  word_count: number | null
  language_id: number
  created_at: string
  coverage_pct: number | null
  mastered_pct: number | null
  has_cover: boolean
  has_audio_overlay: boolean
  audio_overlay_status: "none" | "pending" | "in_progress" | "complete" | "failed"
}

export interface BookDetail extends BookListItem {
  type: string
  chapter_count: number | null
  page_count: number | null
  language_code: string
  register: string | null
  has_audio: boolean
  audio_duration_ms: number | null
  tts_status: "none" | "pending" | "in_progress" | "complete" | "failed"
  video_id: string | null
  source_url: string | null
}

/** Build the authenticated URL for a book cover image. Safe to use as `<img src>` —
 *  the access token is carried as a query param since <img> cannot set headers.
 *  Returns null when the book has no cover so callers can fall back to a placeholder. */
export function bookCoverUrl(bookId: string, hasCover: boolean): string | null {
  if (!hasCover) return null
  const { accessToken } = getAuthStore()
  const url = new URL(`${env.apiUrl}/books/${bookId}/cover`)
  if (accessToken) url.searchParams.set("token", accessToken)
  return url.toString()
}

export interface TokenWithStatus {
  id?: string  // Word DB UUID; undefined if word not in vocabulary
  w: string
  l: string
  pos: string
  r: string
  pi: number  // paragraph index within the page
  si: number  // sentence index within the page (global)
  g: string
  f: string   // morphological features, e.g. "Gender=Masc|Number=Sing|Case=Nom"
  dep_head?: number  // 1-based head token index within sentence (0 = root)
  dep_rel?: string   // Universal Dependency relation label, e.g. "nsubj", "obj"
  hint?: string | null
  status: "new" | "learning" | "known" | "ignored" | "well_known"
  d?: number | null  // difficulty score 0-100
}

export interface PageResponse {
  id: string
  page_number: number
  chapter_number: number | null
  chapter_name: string | null
  chapter_page_number: number | null
  status: "pending" | "ready"
  text: string
  tokens: TokenWithStatus[]
}

export interface PageListResponse {
  items: PageResponse[]
  total: number
  page: number
  limit: number
}

export interface BookUploadResponse {
  id: string
  title: string
  status: string
  language_id: number
}

export async function listBooks(): Promise<{ items: BookListItem[]; total: number }> {
  return apiClient("/books")
}

export async function getBook(id: string): Promise<BookDetail> {
  return apiClient(`/books/${id}`)
}

export async function uploadBook(
  file: File,
  languageId: number,
  title: string,
  register?: string | null
): Promise<BookUploadResponse> {
  const form = new FormData()
  form.append("file", file)
  form.append("language_id", String(languageId))
  form.append("title", title)
  if (register) form.append("register", register)
  return apiUpload("/books", form)
}

export async function deleteBook(id: string): Promise<void> {
  await apiClient(`/books/${id}`, { method: "DELETE" })
}

/** Re-run SMIL audio alignment for an existing book. The extracted audio
 *  files on disk are reused; only sentence_alignments rows are rebuilt. */
export async function realignSmilAudio(id: string): Promise<{ status: string }> {
  return apiClient(`/books/${id}/audio/realign-smil`, { method: "POST" })
}

export async function getBookPages(
  bookId: string,
  page = 1,
  limit = 1
): Promise<PageListResponse> {
  return apiClient(`/books/${bookId}/pages?page=${page}&limit=${limit}`)
}

export interface ChapterSummary {
  chapter_number: number
  chapter_name: string | null
  first_page_number: number
  page_count: number
}

export async function getBookChapters(bookId: string): Promise<ChapterSummary[]> {
  return apiClient(`/books/${bookId}/chapters`)
}
