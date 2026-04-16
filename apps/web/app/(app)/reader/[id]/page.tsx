"use client"

import { useEffect, useCallback, use, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { ArrowLeft, AlignLeft, ExternalLink, List, Mic2, Volume2 } from "lucide-react"
import Link from "next/link"
import { getBook, getBookPages, type PageListResponse } from "@/src/lib/api/books"
import { getAlignmentsForPage, getTimeIndex } from "@/src/lib/api/audio"
import { getReadingProgress, saveReadingProgress, getAudioProgress, saveAudioProgress } from "@/src/lib/reading-progress"
import { batchUpsertWordStatus, recordExposures } from "@/src/lib/api/vocabulary"
import { getLemmaKey } from "@/src/lib/tokens"
import { useReaderStore } from "@/src/stores/reader"
import { useAudioPlayerStore } from "@/src/stores/audioPlayer"
import { useReaderSettings } from "@/src/stores/readerSettings"
import { recordActivity } from "@/src/lib/api/activity"
import { groupBySentence } from "@/src/lib/sentences"
import { listLanguages, resolveReaderConfig, type ReaderConfig } from "@/src/lib/api/languages"
import { ReadingPane } from "@/src/components/reader/ReadingPane"
import { SentenceView } from "@/src/components/reader/SentenceView"
import { KaraokeView } from "@/src/components/reader/KaraokeView"
import { AudioPlayer } from "@/src/components/reader/AudioPlayer"
import { DashAudioPlayer } from "@/src/components/reader/DashAudioPlayer"
import { YouTubePlayer } from "@/src/components/reader/YouTubePlayer"
import { YouTubeReadingPane } from "@/src/components/reader/YouTubeReadingPane"
import { AudioUploadPanel } from "@/src/components/books/AudioUploadPanel"
import { DefinitionPanel } from "@/src/components/reader/DefinitionPanel"
import { ChapterSidebar } from "@/src/components/reader/ChapterSidebar"
import { Badge } from "@/src/components/ui/Badge"

type ViewMode = "page" | "sentence" | "karaoke"

export default function ReaderPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const router = useRouter()
  const searchParams = useSearchParams()
  const page = Number(searchParams.get("page") ?? "1")
  const sentenceParam = Number(searchParams.get("sentence") ?? "0")
  const { activeToken, clearActive, setActiveToken, selectedText, setPanelAnchor, setSentenceContext } = useReaderStore()
  const queryClient = useQueryClient()

  const [viewMode, setViewMode] = useState<ViewMode>("page")
  const [sentenceIndex, setSentenceIndex] = useState(sentenceParam)
  const [showAudioPanel, setShowAudioPanel] = useState(false)
  const { setAlignments, seekTo, setTimeIndex, setOnPageChange, clearTimeIndex, reset: resetAudio } = useAudioPlayerStore()
  const { autoMarkRead } = useReaderSettings()

  // Wipe audio-player state when switching books. Without this, alignments
  // and activeSentenceIndex leak from the previous book — e.g. the amber
  // sentence underline disappears or shows on the wrong sentence when you
  // navigate from an audiobook to a website import (no audio) and back.
  useEffect(() => {
    resetAudio()
    return resetAudio
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const { data: book, isLoading, isError } = useQuery({
    queryKey: ["book", id],
    queryFn: () => getBook(id),
    refetchInterval: (query) =>
      query.state.data?.status === "processing" ? 3000 : false,
  })

  // Fetch page data for sentence mode (karaoke fetches its own via same query key)
  const { data: pageData } = useQuery({
    queryKey: ["book-pages", id, page],
    queryFn: () => getBookPages(id, page, 1),
    placeholderData: (prev) => prev,
    enabled: viewMode === "sentence",
  })

  const hasAudio = Boolean(book?.has_audio_overlay && book?.audio_overlay_status === "complete")
  const hasTts = Boolean(book?.tts_status === "complete")
  const isYouTube = book?.type === "youtube" && book?.status === "completed"
  const isWebsite = book?.type === "website" && book?.status === "completed"

  // Fetch full time-index for YouTube (binary search for video-driven nav)
  const { data: timeIndexData } = useQuery({
    queryKey: ["time-index", id],
    queryFn: () => getTimeIndex(id),
    enabled: isYouTube,
    staleTime: Infinity,
  })

  // Load time-index into store and register page-change callback
  useEffect(() => {
    if (!timeIndexData) return
    setTimeIndex(timeIndexData)
    return () => { clearTimeIndex() }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeIndexData])

  // Register setPage as the callback for video-driven page changes
  const videoSetPage = useCallback((p: number) => {
    if (autoMarkRead && book) autoAdvanceNewWords(book.language_id)
    if (book) recordActivity(book.language_id).catch(() => {})
    saveReadingProgress(id, p)
    const params = new URLSearchParams(searchParams)
    params.set("page", String(p))
    params.delete("sentence")
    router.replace(`/reader/${id}?${params}`, { scroll: false })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, searchParams, router, autoMarkRead, book])

  useEffect(() => {
    if (isYouTube) {
      setOnPageChange(videoSetPage)
      return () => { setOnPageChange(null) }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isYouTube, videoSetPage])

  // Fetch per-page alignments for SMIL/EPUB audio (not YouTube)
  const { data: alignmentsData } = useQuery({
    queryKey: ["alignments", id, page],
    queryFn: () => getAlignmentsForPage(id, page),
    enabled: hasAudio && !isYouTube,
    staleTime: Infinity,
  })

  // Sync per-page alignments into audio player store on page change (SMIL only).
  useEffect(() => {
    if (!alignmentsData) return
    setAlignments(alignmentsData)
    if (alignmentsData.length > 0) {
      const { isPlaying } = useAudioPlayerStore.getState()
      if (isPlaying) {
        const first = alignmentsData[0]
        seekTo(first.audio_start_ms, first.audio_file ?? null)
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alignmentsData])

  // Save YouTube video position (throttled to every 3 seconds)
  useEffect(() => {
    if (!isYouTube) return
    let lastSave = 0
    const unsub = useAudioPlayerStore.subscribe((state) => {
      const now = Date.now()
      if (state.currentTimeMs > 0 && now - lastSave > 3000) {
        lastSave = now
        saveAudioProgress(id, state.currentTimeMs, null)
      }
    })
    return unsub
  }, [isYouTube, id])

  // Restore YouTube video position on mount
  useEffect(() => {
    if (!isYouTube || !timeIndexData?.length) return
    const saved = getAudioProgress(id)
    if (saved && saved.timeMs > 0) {
      seekTo(saved.timeMs)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isYouTube, timeIndexData])

  const sentences = groupBySentence(pageData?.items[0]?.tokens ?? [])

  const { data: languages } = useQuery({
    queryKey: ["languages"],
    queryFn: listLanguages,
    staleTime: Infinity,
  })
  const readerConfig: ReaderConfig | undefined = languages && book
    ? resolveReaderConfig(languages.find(l => l.code === book.language_code) ?? { reader_config: {} })
    : undefined

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

  // Keyboard navigation (page mode only — sentence and karaoke modes handle their own)
  // Page nav: ArrowLeft/K = prev, ArrowRight/J = next. Escape closes panel.
  // Status shortcuts 1–5 live in DefinitionPanel (only when a token is active).
  useEffect(() => {
    if (viewMode !== "page") return
    function handleKey(e: KeyboardEvent) {
      // Don't hijack keys when the user is in an input or selecting text.
      // Shift/Ctrl/Alt+Arrow are browser text-selection shortcuts — let them through.
      const target = e.target as HTMLElement | null
      if (target && (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target.isContentEditable)) {
        return
      }
      if (e.ctrlKey || e.shiftKey || e.altKey || e.metaKey) return

      const pageCount = book?.page_count ?? 1
      // Space is intentionally left to the browser for natural scroll within a page.
      const isPrev = e.key === "ArrowLeft" || e.key === "k" || e.key === "K"
      const isNext = e.key === "ArrowRight" || e.key === "j" || e.key === "J"

      if (isPrev && page > 1) {
        e.preventDefault()
        setPage(page - 1)
        return
      }
      if (isNext && book && page < pageCount) {
        e.preventDefault()
        setPage(page + 1)
        return
      }
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
          const key = getLemmaKey(t)
          if (seen.has(key)) return false
          seen.add(key)
          return true
        })
        .map((t) => ({
          word: getLemmaKey(t),
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
      recordExposures(items.map((i) => i.word), languageId).catch(() => {})
    }
  }

  function setPage(p: number) {
    if (autoMarkRead && book) autoAdvanceNewWords(book.language_id)
    if (book) recordActivity(book.language_id).catch(() => {})
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
  const usesContinuousScroll = isYouTube

  function handleAudioPageEnd() {
    if (page < totalPages) setPage(page + 1)
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Top bar — pt accounts for the status bar safe area in PWA/fullscreen mode */}
      <header
        className="flex items-center gap-4 border-b border-zinc-800 bg-zinc-900 px-6 pb-3"
        style={{ paddingTop: "calc(var(--sat) + 0.75rem)" }}
      >
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
        {book.source_url && (
          <a
            href={book.source_url}
            target="_blank"
            rel="noopener noreferrer"
            title="Open original"
            className="rounded p-1 text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-300"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
        <Badge variant="zinc" className="capitalize">{language}</Badge>
        {!isYouTube && (
          <span className="text-xs text-zinc-500">
            {page} / {totalPages}
          </span>
        )}

        {/* View mode toggle — not for YouTube */}
        {!isYouTube && !isWebsite && (
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
            <button
              onClick={() => setViewMode("karaoke")}
              title="Karaoke view"
              className={`rounded p-1.5 transition ${viewMode === "karaoke" ? "bg-zinc-600 text-zinc-100" : "text-zinc-400 hover:text-zinc-200"}`}
            >
              <Mic2 className="h-3.5 w-3.5" />
            </button>
          </div>
        )}

        {/* Audio panel toggle — only for completed books, not YouTube */}
        {!isYouTube && !isWebsite && book.status === "completed" && (
          <button
            onClick={() => setShowAudioPanel((v) => !v)}
            title="Audio"
            className={`rounded p-1.5 transition ${showAudioPanel ? "text-blue-400" : "text-zinc-400 hover:text-zinc-200"}`}
          >
            <Volume2 className="h-3.5 w-3.5" />
          </button>
        )}
      </header>

      {/* Progress bar — not for YouTube */}
      {!isYouTube && (
        <div className="h-0.5 w-full bg-zinc-800">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${Math.round((page / totalPages) * 100)}%` }}
          />
        </div>
      )}

      {/* Audio upload panel (collapsed by default) */}
      {showAudioPanel && !isYouTube && !isWebsite && book.status === "completed" && (
        <div className="border-b border-zinc-800 bg-zinc-900/80 px-6 py-3">
          <AudioUploadPanel book={book} />
        </div>
      )}

      {/* Main area */}
      {isYouTube || usesContinuousScroll ? (
        /* YouTube / short website: continuous scroll */
        <div className="flex flex-1 flex-col overflow-hidden">
          {isYouTube && book.video_id && <YouTubePlayer videoId={book.video_id} />}
          <div className="flex flex-1 overflow-hidden">
            <YouTubeReadingPane
              bookId={id}
              totalPages={totalPages}
              languageCode={language}
            />
            {(activeToken || selectedText) && (
              <DefinitionPanel
                token={activeToken}
                language={language}
                languageId={book.language_id}
                languageCode={language}
                bookId={book.id}
                currentPage={page}
                register={book.register}
                readerConfig={readerConfig}
              />
            )}
          </div>
        </div>
      ) : (
        /* Books + websites: paginated reading pane */
        <div className="flex flex-1 overflow-hidden">
          {viewMode === "page" && !isWebsite && (
            <ChapterSidebar bookId={id} currentPage={page} onPageChange={setPage} />
          )}
          <div className="flex-1 overflow-hidden">
            {viewMode === "page" ? (
              <ReadingPane
                bookId={id}
                page={page}
                totalPages={totalPages}
                languageCode={language}
                languageId={book.language_id}
                onPageChange={setPage}
                onFinish={() => {
                  if (autoMarkRead && book) autoAdvanceNewWords(book.language_id)
                  if (book) recordActivity(book.language_id).catch(() => {})
                  queryClient.invalidateQueries({ queryKey: ["books"] })
                  router.push("/library")
                }}
              />
            ) : viewMode === "karaoke" ? (
              <KaraokeView
                bookId={id}
                page={page}
                languageCode={language}
                languageId={book.language_id}
              />
            ) : (
              <SentenceView
                sentences={sentences}
                currentIndex={sentenceIndex}
                totalPages={totalPages}
                page={page}
                languageCode={language}
                languageId={book.language_id}
                bookId={id}
                activeToken={activeToken}
                onAdvance={advanceSentence}
                onBack={backSentence}
                onNextPage={() => setPage(page + 1)}
                onPrevPage={() => setPage(page - 1)}
                onTokenClick={(token, e) => {
                  if (activeToken?.w === token.w && activeToken?.si === token.si) {
                    setActiveToken(null)
                    setPanelAnchor(null)
                    setSentenceContext(null)
                  } else {
                    setActiveToken(token)
                    const rect = e.currentTarget.getBoundingClientRect()
                    setPanelAnchor({ x: rect.left + rect.width / 2, top: rect.top, bottom: rect.bottom })
                    const sentenceTokens = sentences.find(s => s.length > 0 && s[0].si === token.si) ?? []
                    setSentenceContext(sentenceTokens.filter(t => t.pos !== "PUNCT").map(t => t.w).join(" ").trim() || null, sentenceTokens)
                  }
                }}
              />
            )}
          </div>
          {(activeToken || selectedText) && (
            <DefinitionPanel
              token={activeToken}
              language={language}
              languageId={book.language_id}
              languageCode={language}
              bookId={book.id}
              currentPage={page}
              register={book.register}
              readerConfig={readerConfig}
            />
          )}
        </div>
      )}

      {hasAudio && (
        <AudioPlayer bookId={id} totalDurationMs={book.audio_duration_ms} onPageEnd={handleAudioPageEnd} />
      )}
      {!hasAudio && !isYouTube && hasTts && (
        <DashAudioPlayer bookId={id} pageNumber={page} onPageEnd={handleAudioPageEnd} />
      )}
    </div>
  )
}
