"use client"

import { Fragment, useEffect, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { ChevronLeft, ChevronRight, CheckCircle2 } from "lucide-react"
import type { TokenWithStatus } from "@/src/lib/api/books"
import { getBookPages } from "@/src/lib/api/books"
import { useReaderStore } from "@/src/stores/reader"
import { useAudioPlayerStore } from "@/src/stores/audioPlayer"
import { useReaderSettings, FONT_SIZE_CLASS, LINE_SPACING_CLASS, TEXT_WIDTH_CLASS } from "@/src/stores/readerSettings"
import { sentenceText } from "@/src/lib/sentences"
import { WordToken } from "./WordToken"
import { PageOptionsMenu } from "./PageOptionsMenu"

const MAX_SELECTION_CHARS = 500

// Languages where tokens are not separated by spaces (Chinese, Japanese, etc.)
function isNoSpaceLanguage(code: string): boolean {
  return code.startsWith("zh") || code === "ja"
}

interface ParagraphsProps {
  tokens: TokenWithStatus[]
  activeToken: TokenWithStatus | null
  selectionRange: [number, number] | null
  noWordSpacing: boolean
  activeSentenceIndex: number | null
  fontSizeClass: string
  lineSpacingClass: string
  onTokenClick: (token: TokenWithStatus, e: React.MouseEvent<HTMLSpanElement>) => void
}

function Paragraphs({
  tokens,
  activeToken,
  selectionRange,
  noWordSpacing,
  activeSentenceIndex,
  fontSizeClass,
  lineSpacingClass,
  onTokenClick,
}: ParagraphsProps) {
  // Group by paragraph while preserving flat index
  const groups: Array<Array<{ token: TokenWithStatus; idx: number }>> = []
  tokens.forEach((token, idx) => {
    if (!groups[token.pi]) groups[token.pi] = []
    groups[token.pi].push({ token, idx })
  })

  return (
    <div className="space-y-5">
      {groups.map((paraTokens, pi) => (
        <p key={pi} className={`${lineSpacingClass} ${fontSizeClass} text-zinc-200`}>
          {paraTokens.map(({ token, idx }, i) => {
            const isHighlighted =
              selectionRange !== null &&
              idx >= selectionRange[0] &&
              idx <= selectionRange[1]
            const prevToken = paraTokens[i - 1]?.token
            const prevW = prevToken?.w ?? ""
            const isClosingPunct = /^[.,!?;:)\]»…\-—–。，！？；：」』]/.test(token.w)
            const prevIsOpeningPunct = /^[(\[«「『]$/.test(prevW)
            const spaceBefore = !noWordSpacing && i > 0 && !isClosingPunct && !prevIsOpeningPunct
            const isActiveSentence = activeSentenceIndex !== null && token.si === activeSentenceIndex
            const prevIsActiveSentence = activeSentenceIndex !== null && prevToken?.si === activeSentenceIndex
            const spaceIsActive = spaceBefore && isActiveSentence && prevIsActiveSentence
            return (
              <Fragment key={`${pi}-${token.si}-${i}`}>
                {spaceBefore && (
                  spaceIsActive
                    ? <span className="underline decoration-amber-400 decoration-2 underline-offset-2"> </span>
                    : " "
                )}
                <WordToken
                  token={token}
                  tokenIndex={idx}
                  isActive={activeToken?.w === token.w && activeToken?.si === token.si}
                  isHighlighted={isHighlighted}
                  isAudioActive={isActiveSentence}
                  onClick={onTokenClick}
                />
              </Fragment>
            )
          })}
        </p>
      ))}
    </div>
  )
}

interface ReadingPaneProps {
  bookId: string
  page: number
  totalPages: number
  languageCode: string
  onPageChange: (page: number) => void
  onFinish?: () => void
}

export function ReadingPane({ bookId, page, totalPages, languageCode, onPageChange, onFinish }: ReadingPaneProps) {
  const noWordSpacing = isNoSpaceLanguage(languageCode)
  const { activeToken, setActiveToken, setSelectedText, setPanelAnchor, setSentenceContext } = useReaderStore()
  const { activeSentenceIndex, seekToSentence, seekTo } = useAudioPlayerStore()
  const { fontSize, lineSpacing, textWidth } = useReaderSettings()

  const containerRef = useRef<HTMLDivElement>(null)
  // Set to true after committing a text selection so the subsequent click event
  // on the token under the pointer does not re-open word mode.
  const selectionJustCommittedRef = useRef(false)
  const [selectionRange, setSelectionRange] = useState<[number, number] | null>(null)

  // Swipe navigation
  const touchStartRef = useRef<{ x: number; y: number } | null>(null)

  // Scroll position restore
  const scrollRestoredRef = useRef(false)
  useEffect(() => { scrollRestoredRef.current = false }, [page])

  // Save scroll position on scroll (debounced 500ms)
  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    let timer: ReturnType<typeof setTimeout>
    const handleScroll = () => {
      clearTimeout(timer)
      timer = setTimeout(() => {
        localStorage.setItem(`slovo-scroll-${bookId}-${page}`, String(container.scrollTop))
      }, 500)
    }
    container.addEventListener("scroll", handleScroll, { passive: true })
    return () => { clearTimeout(timer); container.removeEventListener("scroll", handleScroll) }
  }, [bookId, page])

  const { data, isLoading } = useQuery({
    queryKey: ["book-pages", bookId, page],
    queryFn: () => getBookPages(bookId, page, 1),
    placeholderData: (prev) => prev,
    refetchInterval: (query) =>
      query.state.data?.items[0]?.status === "pending" ? 3000 : false,
  })

  const currentPage = data?.items[0]

  // Restore scroll position once data loads for this page
  useEffect(() => {
    if (!currentPage || scrollRestoredRef.current) return
    scrollRestoredRef.current = true
    const container = containerRef.current
    if (!container) return
    const saved = localStorage.getItem(`slovo-scroll-${bookId}-${page}`)
    if (saved) container.scrollTop = Number(saved)
  }, [currentPage, bookId, page])

  /**
   * Called on mouseup and touchend. Reads the native browser selection and,
   * if it spans 2+ tokens, commits it as a phrase selection.
   */
  function commitNativeSelection() {
    const sel = window.getSelection()
    if (!sel || sel.isCollapsed || sel.rangeCount === 0 || !currentPage) return

    const range = sel.getRangeAt(0)
    const container = containerRef.current
    if (!container || !range.intersectsNode(container)) return

    const selectedString = sel.toString().trim()
    if (!selectedString || selectedString.length < 2) return

    // Find all token elements that the selection range covers
    const tokenEls = container.querySelectorAll("[data-token-index]")
    const indices: number[] = []
    tokenEls.forEach((el) => {
      if (range.intersectsNode(el)) {
        const idx = parseInt(el.getAttribute("data-token-index") ?? "", 10)
        if (!isNaN(idx)) indices.push(idx)
      }
    })

    if (indices.length < 2) {
      setSelectionRange(null)
      return
    }

    const lo = Math.min(...indices)
    const hi = Math.max(...indices)
    setSelectionRange([lo, hi])

    const tokens = currentPage.tokens.slice(lo, hi + 1)
    const sep = noWordSpacing ? "" : " "
    const text = tokens.map((t) => t.w).join(sep).trim()

    setSelectedText(text.slice(0, MAX_SELECTION_CHARS * 2), tokens)
    selectionJustCommittedRef.current = true

    // Anchor the panel near the selection
    const selRect = range.getBoundingClientRect()
    if (selRect.width > 0) {
      setPanelAnchor({ x: selRect.left + selRect.width / 2, top: selRect.top, bottom: selRect.bottom })
    }

    // Replace the native selection highlight with our custom token highlight
    sel.removeAllRanges()
  }

  function handleTouchStart(e: React.TouchEvent) {
    touchStartRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY }
  }

  function handleTouchEnd(e: React.TouchEvent) {
    if (touchStartRef.current) {
      const touch = e.changedTouches[0]
      const dx = touch.clientX - touchStartRef.current.x
      const dy = touch.clientY - touchStartRef.current.y
      touchStartRef.current = null
      // Horizontal swipe: more than 60px horizontal, dominantly horizontal
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy)) {
        if (dx < 0 && page < totalPages) onPageChange(page + 1)
        else if (dx > 0 && page > 1) onPageChange(page - 1)
        return
      }
    }
    // Small delay to let iOS finalise the selection object before we read it
    setTimeout(commitNativeSelection, 50)
  }

  function handleTokenClick(token: TokenWithStatus, e: React.MouseEvent<HTMLSpanElement>) {
    // Suppress word-click when a phrase selection was just committed (mouseup
    // fires before click, so the flag is already set here)
    if (selectionJustCommittedRef.current) {
      selectionJustCommittedRef.current = false
      return
    }

    setSelectedText(null)
    setSelectionRange(null)

    if (activeToken?.w === token.w && activeToken?.si === token.si) {
      setActiveToken(null)
      setPanelAnchor(null)
      setSentenceContext(null)
    } else {
      setActiveToken(token)
      const rect = e.currentTarget.getBoundingClientRect()
      setPanelAnchor({ x: rect.left + rect.width / 2, top: rect.top, bottom: rect.bottom })

      // Extract sentence context for DefinitionPanel and Anki
      if (currentPage) {
        const sentenceTokens = currentPage.tokens.filter((t) => t.si === token.si)
        setSentenceContext(sentenceText(sentenceTokens, noWordSpacing), sentenceTokens)
      }
    }

    // Seek audio to the start of the clicked sentence (no-op if no alignments)
    const target = seekToSentence(token.si)
    if (target) seekTo(target.ms, target.audioFile)
  }

  return (
    <div className="flex h-full flex-col">
      <div
        ref={containerRef}
        className="flex-1 overflow-y-auto px-12 py-8"
        onMouseUp={commitNativeSelection}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
        onDragStart={(e) => e.preventDefault()}
      >
        {isLoading ? (
          <div className="animate-pulse space-y-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-5 rounded bg-zinc-800" style={{ width: `${70 + (i % 3) * 10}%` }} />
            ))}
          </div>
        ) : currentPage ? (
          <div className={`mx-auto ${TEXT_WIDTH_CLASS[textWidth]}`}>
            {currentPage.chapter_name && (
              <p className="mb-8 text-sm font-medium uppercase tracking-widest text-zinc-500">
                {currentPage.chapter_name}
              </p>
            )}
            {currentPage.status === "pending" ? (
              <div className="flex flex-col items-center gap-3 py-16 text-zinc-500">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-zinc-700 border-t-blue-500" />
                <p className="text-sm">This page is being processed…</p>
              </div>
            ) : (
              <Paragraphs
                tokens={currentPage.tokens}
                activeToken={activeToken}
                selectionRange={selectionRange}
                noWordSpacing={noWordSpacing}
                activeSentenceIndex={activeSentenceIndex}
                fontSizeClass={FONT_SIZE_CLASS[fontSize]}
                lineSpacingClass={LINE_SPACING_CLASS[lineSpacing]}
                onTokenClick={handleTokenClick}
              />
            )}
          </div>
        ) : (
          <p className="text-center text-zinc-500">No content on this page.</p>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-zinc-800 px-8 py-4">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-100 disabled:opacity-30"
        >
          <ChevronLeft className="h-4 w-4" />
          Previous
        </button>
        <div className="flex items-center gap-3">
          <span className="text-sm text-zinc-500">Page {page} of {totalPages}</span>
          <PageOptionsMenu />
        </div>
        {page >= totalPages ? (
          <button
            onClick={onFinish}
            className="flex items-center gap-1.5 rounded-lg bg-emerald-600/20 px-3 py-2 text-sm font-medium text-emerald-400 transition hover:bg-emerald-600/30"
          >
            <CheckCircle2 className="h-4 w-4" />
            Finish
          </button>
        ) : (
          <button
            onClick={() => onPageChange(page + 1)}
            className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-100"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  )
}
