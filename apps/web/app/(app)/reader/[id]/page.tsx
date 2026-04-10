"use client"

import { useEffect, use, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, AlignLeft, List } from "lucide-react"
import Link from "next/link"
import { getBook, getBookPages, type PageListResponse } from "@/src/lib/api/books"
import { getReadingProgress, saveReadingProgress } from "@/src/lib/reading-progress"
import { batchUpsertWordStatus } from "@/src/lib/api/vocabulary"
import { useReaderStore } from "@/src/stores/reader"
import { groupBySentence } from "@/src/lib/sentences"
import { ReadingPane } from "@/src/components/reader/ReadingPane"
import { SentenceView } from "@/src/components/reader/SentenceView"
import { DefinitionPanel } from "@/src/components/reader/DefinitionPanel"
import { ChapterSidebar } from "@/src/components/reader/ChapterSidebar"
import { Badge } from "@/src/components/ui/Badge"

type ViewMode = "page" | "sentence"

export default function ReaderPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const router = useRouter()
  const searchParams = useSearchParams()
  const page = Number(searchParams.get("page") ?? "1")
  const sentenceParam = Number(searchParams.get("sentence") ?? "0")
  const { activeToken, clearActive, setActiveToken } = useReaderStore()
  const queryClient = useQueryClient()

  const [viewMode, setViewMode] = useState<ViewMode>("page")
  const [sentenceIndex, setSentenceIndex] = useState(sentenceParam)

  const { data: book, isLoading, isError } = useQuery({
    queryKey: ["book", id],
    queryFn: () => getBook(id),
    refetchInterval: (query) =>
      query.state.data?.status === "processing" ? 3000 : false,
  })

  // Fetch page data for sentence mode
  const { data: pageData } = useQuery({
    queryKey: ["book-pages", id, page],
    queryFn: () => getBookPages(id, page, 1),
    placeholderData: (prev) => prev,
    enabled: viewMode === "sentence",
  })

  const sentences = groupBySentence(pageData?.items[0]?.tokens ?? [])

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
    setSentenceIndex(0)
  }, [page, clearActive])

  // Sync sentenceIndex to URL param on mount
  useEffect(() => {
    setSentenceIndex(sentenceParam)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Keyboard navigation (page mode only — sentence mode handles its own)
  useEffect(() => {
    if (viewMode !== "page") return
    function handleKey(e: KeyboardEvent) {
      if (e.key === "ArrowLeft" && page > 1) setPage(page - 1)
      if (e.key === "ArrowRight" && book && page < (book.page_count ?? 1)) setPage(page + 1)
      if (e.key === "Escape") clearActive()
    }
    document.addEventListener("keydown", handleKey)
    return () => document.removeEventListener("keydown", handleKey)
  }, [page, book, clearActive, viewMode])

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
    params.delete("sentence")
    router.replace(`/reader/${id}?${params}`)
  }

  function advanceSentence() {
    const next = sentenceIndex + 1
    setSentenceIndex(next)
    const params = new URLSearchParams(searchParams)
    params.set("sentence", String(next))
    router.replace(`/reader/${id}?${params}`, { scroll: false })
  }

  function backSentence() {
    const prev = Math.max(0, sentenceIndex - 1)
    setSentenceIndex(prev)
    const params = new URLSearchParams(searchParams)
    params.set("sentence", String(prev))
    router.replace(`/reader/${id}?${params}`, { scroll: false })
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

        {/* View mode toggle */}
        <div className="flex rounded-lg border border-zinc-700 bg-zinc-800 p-0.5">
          <button
            onClick={() => setViewMode("page")}
            title="Page view"
            className={`rounded p-1.5 transition ${viewMode === "page" ? "bg-zinc-600 text-zinc-100" : "text-zinc-400 hover:text-zinc-200"}`}
          >
            <List className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => { setViewMode("sentence"); setSentenceIndex(0) }}
            title="Sentence view"
            className={`rounded p-1.5 transition ${viewMode === "sentence" ? "bg-zinc-600 text-zinc-100" : "text-zinc-400 hover:text-zinc-200"}`}
          >
            <AlignLeft className="h-3.5 w-3.5" />
          </button>
        </div>
      </header>

      {/* Main area */}
      <div className="flex flex-1 overflow-hidden">
        {viewMode === "page" && (
          <ChapterSidebar bookId={id} currentPage={page} onPageChange={setPage} />
        )}

        <div className="flex-1 overflow-hidden">
          {viewMode === "page" ? (
            <ReadingPane
              bookId={id}
              page={page}
              totalPages={totalPages}
              languageCode={language}
              onPageChange={setPage}
            />
          ) : (
            <SentenceView
              sentences={sentences}
              currentIndex={sentenceIndex}
              totalPages={totalPages}
              page={page}
              languageCode={language}
              activeToken={activeToken}
              onAdvance={advanceSentence}
              onBack={backSentence}
              onNextPage={() => setPage(page + 1)}
              onPrevPage={() => setPage(page - 1)}
              onTokenClick={(token) => {
                if (activeToken?.w === token.w && activeToken?.si === token.si) {
                  setActiveToken(null)
                } else {
                  setActiveToken(token)
                }
              }}
            />
          )}
        </div>

        {activeToken && (
          <DefinitionPanel
            token={activeToken}
            language={language}
            languageId={book.language_id}
            languageCode={language}
            bookId={book.id}
            currentPage={page}
          />
        )}
      </div>
    </div>
  )
}
