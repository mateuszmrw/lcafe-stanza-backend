import { apiClient, apiUpload } from "./client"

export interface BookListItem {
  id: string
  title: string
  description: string | null
  status: "pending" | "processing" | "completed" | "failed"
  word_count: number | null
  language_id: number
  created_at: string
}

export interface BookDetail extends BookListItem {
  chapter_count: number | null
  page_count: number | null
  language_code: string
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
  status: "new" | "learning" | "known" | "ignored" | "well_known"
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
  title: string
): Promise<BookUploadResponse> {
  const form = new FormData()
  form.append("file", file)
  form.append("language_id", String(languageId))
  form.append("title", title)
  return apiUpload("/books", form)
}

export async function deleteBook(id: string): Promise<void> {
  await apiClient(`/books/${id}`, { method: "DELETE" })
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
