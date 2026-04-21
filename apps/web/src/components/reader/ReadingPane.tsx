"use client"

import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react"
import { ChevronLeft, ChevronRight, CheckCircle2 } from "lucide-react"
import { useQuery } from "@tanstack/react-query"
import type { ConstituencyPhrase, TokenWithStatus } from "@/src/lib/api/books"
import { useReaderStore } from "@/src/stores/reader"
import { useReaderPageLogic } from "@/src/hooks/useReaderPageLogic"
import { useAudioPlayerStore } from "@/src/stores/audioPlayer"
import { useReaderSettings, FONT_SIZE_CLASS, LINE_SPACING_CLASS, TEXT_WIDTH_CLASS } from "@/src/stores/readerSettings"
import { sentenceText } from "@/src/lib/sentences"
import { cn } from "@/src/lib/cn"
import { WordToken } from "./WordToken"
import { PageOptionsMenu } from "./PageOptionsMenu"
import { getBatchCognates, type CognateData } from "@/src/lib/api/vocabulary"
import { getProfile } from "@/src/lib/api/users"

const MAX_SELECTION_CHARS = 500

// Languages where tokens are not separated by spaces (Chinese, Japanese, etc.)
function isNoSpaceLanguage(code: string): boolean {
  return code.startsWith("zh") || code === "ja"
}


// Snap the selection range [lo, hi] to the tightest constituency phrase that
// fully contains it. Returns the original range if no enclosing phrase found.
function snapToConstituent(
  lo: number,
  hi: number,
  tokens: TokenWithStatus[],
  phrases: ConstituencyPhrase[],
): [number, number] {
  if (!phrases.length) return [lo, hi]

  // Build si → sorted list of global token indices
  const siToGlobals = new Map<number, number[]>()
  tokens.forEach((t, i) => {
    const arr = siToGlobals.get(t.si)
    if (arr) arr.push(i)
    else siToGlobals.set(t.si, [i])
  })

  const selSis = new Set(tokens.slice(lo, hi + 1).map((t) => t.si))
  let bestLo = lo
  let bestHi = hi
  let bestSize = Infinity

  for (const phrase of phrases) {
    if (!selSis.has(phrase.si)) continue
    const globals = siToGlobals.get(phrase.si)
    if (!globals) continue
    const plo = globals[phrase.start]
    const phi = globals[phrase.end - 1]
    if (plo === undefined || phi === undefined) continue
    if (plo <= lo && phi >= hi) {
      const size = phi - plo
      if (size < bestSize) {
        bestSize = size
        bestLo = plo
        bestHi = phi
      }
    }
  }

  return [bestLo, bestHi]
}

function getTokenIndexAtPoint(x: number, y: number): number | null {
  const el = document.elementFromPoint(x, y)
  const tokenEl = el?.closest("[data-token-index]")
  if (!tokenEl) return null
  const idx = parseInt(tokenEl.getAttribute("data-token-index") ?? "", 10)
  return isNaN(idx) ? null : idx
}

interface ParagraphsProps {
  tokens: TokenWithStatus[]
  activeToken: TokenWithStatus | null
  selectionRange: [number, number] | null
  noWordSpacing: boolean
  activeSentenceIndex: number | null
  fontSizeClass: string
  lineSpacingClass: string
  phraseTokenIndices: Set<number>
  hoveredChainId: number | null
  cognateMap: Record<string, CognateData>
  onTokenClick: (token: TokenWithStatus, e: React.MouseEvent<HTMLSpanElement>) => void
  onHoverChain: (chainId: number | null) => void
}

function Paragraphs({
  tokens,
  activeToken,
  selectionRange,
  noWordSpacing,
  activeSentenceIndex,
  fontSizeClass,
  lineSpacingClass,
  phraseTokenIndices,
  hoveredChainId,
  cognateMap,
  onTokenClick,
  onHoverChain,
}: ParagraphsProps) {
  // Group by paragraph while preserving flat index
  const groups: Array<Array<{ token: TokenWithStatus; idx: number }>> = []
  tokens.forEach((token, idx) => {
    if (!groups[token.pi]) groups[token.pi] = []
    groups[token.pi].push({ token, idx })
  })

  return (
    <div className="space-y-5">
      {groups.map((paraTokens, pi) => {
        // Collect "segments": consecutive same-mwt tokens become one MWT group.
        type Segment =
          | { mwt: false; entry: { token: TokenWithStatus; idx: number }; paraI: number }
          | { mwt: true; entries: { token: TokenWithStatus; idx: number }[]; paraI: number }
        const segments: Segment[] = []
        paraTokens.forEach((entry, paraI) => {
          const gid = entry.token.mwt_group_id
          if (gid != null) {
            const last = segments[segments.length - 1]
            if (last?.mwt && last.entries[0].token.mwt_group_id === gid) {
              last.entries.push(entry)
              return
            }
            segments.push({ mwt: true, entries: [entry], paraI })
          } else {
            segments.push({ mwt: false, entry, paraI })
          }
        })

        return (
          <p key={pi} className={`${lineSpacingClass} ${fontSizeClass} text-zinc-200`}>
            {segments.map((seg, si) => {
              // For space-before logic, get the first entry and the previous segment's last entry
              const firstEntry = seg.mwt ? seg.entries[0] : seg.entry
              const prevSeg = segments[si - 1]
              const prevEntry = prevSeg
                ? prevSeg.mwt
                  ? prevSeg.entries[prevSeg.entries.length - 1]
                  : prevSeg.entry
                : undefined
              const prevW = prevEntry?.token.w ?? ""
              const isClosingPunct = /^[.,!?;:)\]»…\-—–。，！？；：」』]/.test(firstEntry.token.w)
              const prevIsOpeningPunct = /^[(\[«「『]$/.test(prevW)
              const spaceBefore = !noWordSpacing && si > 0 && !isClosingPunct && !prevIsOpeningPunct
              const isActiveSentence = activeSentenceIndex !== null && firstEntry.token.si === activeSentenceIndex
              const prevIsActiveSentence = activeSentenceIndex !== null && prevEntry?.token.si === activeSentenceIndex
              const spaceIsActive = spaceBefore && isActiveSentence && prevIsActiveSentence
              const isSpaceInPhrase = spaceBefore && phraseTokenIndices.has(firstEntry.idx) && prevEntry !== undefined && phraseTokenIndices.has(prevEntry.idx)
              const isSpaceInSelection = spaceBefore && selectionRange !== null &&
                firstEntry.idx >= selectionRange[0] && firstEntry.idx <= selectionRange[1] &&
                prevEntry !== undefined && prevEntry.idx >= selectionRange[0] && prevEntry.idx <= selectionRange[1]
              const spaceClass = cn(
                spaceIsActive && "underline decoration-amber-400 decoration-2 underline-offset-2",
                isSpaceInPhrase && !isSpaceInSelection && "bg-emerald-500/30",
                isSpaceInSelection && "bg-violet-500/40",
              )

              if (!seg.mwt) {
                const { token, idx } = seg.entry
                const isHighlighted = selectionRange !== null && idx >= selectionRange[0] && idx <= selectionRange[1]
                return (
                  <Fragment key={`${pi}-${si}`}>
                    {spaceBefore && (spaceClass ? <span className={spaceClass}> </span> : " ")}
                    <WordToken
                      token={token}
                      tokenIndex={idx}
                      isActive={activeToken?.w === token.w && activeToken?.si === token.si}
                      isHighlighted={isHighlighted}
                      isAudioActive={activeSentenceIndex !== null && token.si === activeSentenceIndex}
                      isPhraseToken={phraseTokenIndices.has(idx)}
                      isCorefHighlighted={hoveredChainId !== null && (token.cc ?? 0) === hoveredChainId && hoveredChainId > 0}
                      cognateData={cognateMap[token.l?.toLowerCase() ?? ""]}
                      onClick={onTokenClick}
                      onHoverChain={onHoverChain}
                    />
                  </Fragment>
                )
              }

              // MWT group — no space between members, dotted underline connects them
              return (
                <Fragment key={`${pi}-${si}`}>
                  {spaceBefore && (spaceClass ? <span className={spaceClass}> </span> : " ")}
                  <span className="inline-flex border-b border-dotted border-zinc-500/60 pb-px">
                    {seg.entries.map(({ token, idx }, mi) => {
                      const isHighlighted = selectionRange !== null && idx >= selectionRange[0] && idx <= selectionRange[1]
                      return (
                        <WordToken
                          key={mi}
                          token={token}
                          tokenIndex={idx}
                          isActive={activeToken?.w === token.w && activeToken?.si === token.si}
                          isHighlighted={isHighlighted}
                          isAudioActive={activeSentenceIndex !== null && token.si === activeSentenceIndex}
                          isPhraseToken={phraseTokenIndices.has(idx)}
                          isCorefHighlighted={hoveredChainId !== null && (token.cc ?? 0) === hoveredChainId && hoveredChainId > 0}
                          cognateData={cognateMap[token.l?.toLowerCase() ?? ""]}
                          onClick={onTokenClick}
                          onHoverChain={onHoverChain}
                        />
                      )
                    })}
                  </span>
                </Fragment>
              )
            })}
          </p>
        )
      })}
    </div>
  )
}

interface ReadingPaneProps {
  bookId: string
  page: number
  totalPages: number
  languageCode: string
  languageId: number
  onPageChange: (page: number) => void
  onFinish?: () => void
}

export function ReadingPane({ bookId, page, totalPages, languageCode, languageId, onPageChange, onFinish }: ReadingPaneProps) {
  const noWordSpacing = isNoSpaceLanguage(languageCode)
  const { activeToken, selectedText, setActiveToken, setSelectedText, setPanelAnchor, setSentenceContext, setActiveCognateData, clearActive } = useReaderStore()
  // Select individual slices so audioPlayer tick() (fires 5x/sec) doesn't
  // re-render the whole pane — only activeSentenceIndex updates matter here.
  const activeSentenceIndex = useAudioPlayerStore((s) => s.activeSentenceIndex)
  const seekToSentence = useAudioPlayerStore((s) => s.seekToSentence)
  const seekTo = useAudioPlayerStore((s) => s.seekTo)
  const { fontSize, lineSpacing, textWidth } = useReaderSettings()

  const containerRef = useRef<HTMLDivElement>(null)
  // Set to true after committing a text selection so the subsequent click event
  // on the token under the pointer does not re-open word mode.
  const selectionJustCommittedRef = useRef(false)
  const [selectionRange, setSelectionRange] = useState<[number, number] | null>(null)

  // Clear token highlight when the panel is dismissed from outside ReadingPane
  // (e.g. DefinitionPanel backdrop click calls clearActive() but can't reach setSelectionRange)
  useEffect(() => {
    if (!selectedText) setSelectionRange(null)
  }, [selectedText])

  const isDraggingRef = useRef(false)
  const dragStartIdxRef = useRef<number | null>(null)
  const dragPointerIdRef = useRef<number | null>(null)
  const longPressTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

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

  const [hoveredChainId, setHoveredChainId] = useState<number | null>(null)
  const handleHoverChain = useCallback((id: number | null) => setHoveredChainId(id), [])

  const { currentPage, isLoading, phraseTokenIndices, constituentPhrases } = useReaderPageLogic({
    bookId,
    page,
    languageId,
    noWordSpacing,
  })

  const l2Code = languageCode.slice(0, 2).toLowerCase()
  const { data: profile } = useQuery({ queryKey: ["profile"], queryFn: getProfile, staleTime: Infinity })
  const nativeLang = profile?.native_language_code ?? null
  const pageLemmas = useMemo(() => {
    if (!currentPage) return []
    return [...new Set(currentPage.tokens.map((t) => t.l?.toLowerCase()).filter(Boolean))] as string[]
  }, [currentPage])
  const { data: cognateMap = {} as Record<string, CognateData> } = useQuery({
    queryKey: ["cognates", bookId, page, l2Code, nativeLang],
    queryFn: () => getBatchCognates(pageLemmas, l2Code, nativeLang ?? undefined),
    enabled: pageLemmas.length > 0 && !!nativeLang && nativeLang !== l2Code,
    staleTime: Infinity,
  })

  // Restore scroll position once data loads for this page
  useEffect(() => {
    if (!currentPage || scrollRestoredRef.current) return
    scrollRestoredRef.current = true
    const container = containerRef.current
    if (!container) return
    const saved = localStorage.getItem(`slovo-scroll-${bookId}-${page}`)
    if (saved) container.scrollTop = Number(saved)
  }, [currentPage, bookId, page])

  function handlePointerDown(e: React.PointerEvent<HTMLDivElement>) {
    if (!e.isPrimary || e.button !== 0) return
    const idx = getTokenIndexAtPoint(e.clientX, e.clientY)
    dragStartIdxRef.current = idx
    dragPointerIdRef.current = e.pointerId
    isDraggingRef.current = false
    // Do NOT setPointerCapture here — it redirects the click event to the container,
    // breaking child onClick handlers. Capture is deferred to when drag actually starts.
    if (idx !== null && currentPage?.tokens[idx]) {
      const si = currentPage.tokens[idx].si
      longPressTimerRef.current = setTimeout(() => {
        longPressTimerRef.current = null
        dragStartIdxRef.current = null
        isDraggingRef.current = false
        const target = seekToSentence(si)
        if (target) seekTo(target.ms, target.audioFile)
        // Suppress the click that fires after pointerup
        selectionJustCommittedRef.current = true
      }, 500)
    }
  }

  function handlePointerMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!e.isPrimary || dragStartIdxRef.current === null) return
    const idx = getTokenIndexAtPoint(e.clientX, e.clientY)
    if (idx === null || idx === dragStartIdxRef.current) return
    if (!isDraggingRef.current) {
      isDraggingRef.current = true
      // Cancel long press — user is dragging, not holding
      if (longPressTimerRef.current !== null) {
        clearTimeout(longPressTimerRef.current)
        longPressTimerRef.current = null
      }
      // Capture pointer now so we track movement outside the container
      if (dragPointerIdRef.current !== null) {
        containerRef.current?.setPointerCapture(dragPointerIdRef.current)
      }
    }
    const lo = Math.min(dragStartIdxRef.current, idx)
    const hi = Math.max(dragStartIdxRef.current, idx)
    setSelectionRange([lo, hi])
  }

  function handlePointerUp(e: React.PointerEvent<HTMLDivElement>) {
    if (!e.isPrimary) return
    if (longPressTimerRef.current !== null) {
      clearTimeout(longPressTimerRef.current)
      longPressTimerRef.current = null
    }
    const startIdx = dragStartIdxRef.current
    dragStartIdxRef.current = null
    dragPointerIdRef.current = null
    if (!isDraggingRef.current || startIdx === null || !currentPage) {
      isDraggingRef.current = false
      return
    }
    isDraggingRef.current = false

    const endIdx = getTokenIndexAtPoint(e.clientX, e.clientY) ?? startIdx
    let lo = Math.min(startIdx, endIdx)
    let hi = Math.max(startIdx, endIdx)
    if (hi <= lo) { setSelectionRange(null); return }

    ;[lo, hi] = snapToConstituent(lo, hi, currentPage.tokens, constituentPhrases)
    setSelectionRange([lo, hi])

    const tokens = currentPage.tokens.slice(lo, hi + 1)
    const sep = noWordSpacing ? "" : " "
    const text = tokens.map((t) => t.w).join(sep).trim()
    if (!text || text.length < 2) { setSelectionRange(null); return }

    setSelectedText(text.slice(0, MAX_SELECTION_CHARS * 2), tokens)
    selectionJustCommittedRef.current = true

    const container = containerRef.current
    if (container) {
      const firstEl = container.querySelector(`[data-token-index="${lo}"]`)
      const lastEl = container.querySelector(`[data-token-index="${hi}"]`)
      if (firstEl && lastEl) {
        const firstRect = firstEl.getBoundingClientRect()
        const lastRect = lastEl.getBoundingClientRect()
        setPanelAnchor({
          x: e.clientX,
          top: Math.min(firstRect.top, lastRect.top),
          bottom: Math.max(firstRect.bottom, lastRect.bottom),
        })
      }
    }
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
      setActiveCognateData(null)
    } else {
      setActiveToken(token)
      setActiveCognateData(cognateMap[token.l?.toLowerCase() ?? ""] ?? null)
      const rect = e.currentTarget.getBoundingClientRect()
      setPanelAnchor({ x: rect.left + rect.width / 2, top: rect.top, bottom: rect.bottom })

      // Extract sentence context for DefinitionPanel and Anki
      if (currentPage) {
        const sentenceTokens = currentPage.tokens.filter((t) => t.si === token.si)
        setSentenceContext(sentenceText(sentenceTokens, noWordSpacing), sentenceTokens)
      }
    }

  }

  /**
   * Click landed on empty space in the reading pane (not on a token).
   * Clears any active word or phrase selection. Must ignore clicks that are
   * the tail end of a selection gesture (the mouseup that committed the
   * selection fires just before this click).
   */
  function handleBackgroundClick(e: React.MouseEvent<HTMLDivElement>) {
    // Token clicks are handled by WordToken's own onClick — bail out.
    const target = e.target as HTMLElement | null
    if (target?.closest("[data-token-index]")) return

    // handlePointerUp ran before this click and set the flag — consume it so the
    // click isn't treated as a "dismiss" gesture after a drag selection.
    if (selectionJustCommittedRef.current) {
      selectionJustCommittedRef.current = false
      return
    }

    if (activeToken || selectedText) {
      clearActive()
      setSelectionRange(null)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div
        ref={containerRef}
        className="select-none flex-1 overflow-y-auto px-12 py-8"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onClick={handleBackgroundClick}
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
                phraseTokenIndices={phraseTokenIndices}
                hoveredChainId={hoveredChainId}
                cognateMap={cognateMap}
                onTokenClick={handleTokenClick}
                onHoverChain={handleHoverChain}
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
