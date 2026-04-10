"use client"

import { useEffect, use } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft } from "lucide-react"
import Link from "next/link"
import { getBook, type PageListResponse } from "@/src/lib/api/books"
import { getReadingProgress, saveReadingProgress } from "@/src/lib/reading-progress"
import { batchUpsertWordStatus } from "@/src/lib/api/vocabulary"
import { useReaderStore } from "@/src/stores/reader"
import { ReadingPane } from "@/src/components/reader/ReadingPane"
import { DefinitionPanel } from "@/src/components/reader/DefinitionPanel"
import { ChapterSidebar } from "@/src/components/reader/ChapterSidebar"
import { Badge } from "@/src/components/ui/Badge"

export default function ReaderPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const router = useRouter()
  const searchParams = useSearchParams()
  const page = Number(searchParams.get("page") ?? "1")
  const { activeToken, clearActive } = useReaderStore()
  const queryClient = useQueryClient()

  const { data: book, isLoading, isError } = useQuery({
    queryKey: ["book", id],
    queryFn: () => getBook(id),
    refetchInterval: (query) =>
      query.state.data?.status === "processing" ? 3000 : false,
  })

  // Restore last-read page if no explicit ?page= param in URL
  useEffect(() => {
    if (searchParams.get("page") === null) {
      const saved = getReadingProgress(id)
      if (saved && saved > 1) {
        const p = new URLSearchParams(searchParams)
        p.set("page", String(saved))
        router.replace(`/reader/${id}?${p}`)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // only on mount

  // Clear active token and selection when changing pages
  useEffect(() => {
    clearActive()
  }, [page, clearActive])

  // Keyboard navigation
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === "ArrowLeft" && page > 1) setPage(page - 1)
      if (e.key === "ArrowRight" && book && page < (book.page_count ?? 1)) setPage(page + 1)
      if (e.key === "Escape") clearActive()
    }
    document.addEventListener("keydown", handleKey)
    return () => document.removeEventListener("keydown", handleKey)
  }, [page, book, clearActive])

  function autoAdvanceNewWords(languageId: number) {
    const cached = queryClient.getQueryData<PageListResponse>(["book-pages", id, page])
    if (!cached) return
    const seen = new Set<string>()
    const items = cached.items.flatMap((p) =>
      p.tokens
        .filter((t) => t.status === "new")
        .filter((t) => {
          const key = t.w.toLowerCase()
          if (seen.has(key)) return false
          seen.add(key)
          return true
        })
        .map((t) => ({
          word: t.w,
          status: "well_known" as const,
          language_id: languageId,
          lemma: t.l,
          pos: t.pos,
          reading: t.r,
          gender: t.g,
          feats: t.f,
        }))
    )
    if (items.length > 0) {
      batchUpsertWordStatus(items).catch(() => {})
    }
  }

  function setPage(p: number) {
    if (book && p === page + 1) autoAdvanceNewWords(book.language_id)
    saveReadingProgress(id, p)
    const params = new URLSearchParams(searchParams)
    params.set("page", String(p))
    router.replace(`/reader/${id}?${params}`)
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-zinc-700 border-t-blue-500" />
      </div>
    )
  }

  if (isError || !book) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4">
        <p className="text-zinc-400">Book not found.</p>
        <Link href="/library" className="text-sm text-blue-400 hover:text-blue-300">
          Back to Library
        </Link>
      </div>
    )
  }

  const totalPages = book.page_count ?? 1
  const language = book.language_code

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Top bar */}
      <header className="flex items-center gap-4 border-b border-zinc-800 bg-zinc-900 px-6 py-3">
        <Link
          href="/library"
          className="flex items-center gap-1 rounded-md p-1 text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-100"
          aria-label="Back to library"
        >
          <ArrowLeft className="h-4 w-4" />
        </Link>
        <h1 className="flex-1 truncate text-sm font-semibold text-zinc-200">
          {book.title}
        </h1>
        <Badge variant="zinc" className="capitalize">{language}</Badge>
        <span className="text-xs text-zinc-500">
          {page} / {totalPages}
        </span>
      </header>

      {/* Main area */}
      <div className="flex flex-1 overflow-hidden">
        <ChapterSidebar bookId={id} currentPage={page} onPageChange={setPage} />

        <div className="flex-1 overflow-hidden">
          <ReadingPane
            bookId={id}
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
          />
        </div>

        {activeToken && (
          <DefinitionPanel
            token={activeToken}
            language={language}
            languageId={book.language_id}
            languageCode={language}
          />
        )}
      </div>
    </div>
  )
}
