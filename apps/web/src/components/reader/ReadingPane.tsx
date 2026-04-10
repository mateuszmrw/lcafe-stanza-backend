"use client"

import { Fragment, useRef, useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { ChevronLeft, ChevronRight } from "lucide-react"
import type { TokenWithStatus } from "@/src/lib/api/books"
import { getBookPages } from "@/src/lib/api/books"
import { useReaderStore } from "@/src/stores/reader"
import { WordToken } from "./WordToken"

const MAX_SELECTION_CHARS = 500

interface ParagraphsProps {
  tokens: TokenWithStatus[]
  activeToken: TokenWithStatus | null
  selectionRange: [number, number] | null
  onTokenClick: (token: TokenWithStatus) => void
  onTokenMouseDown: (tokenIndex: number) => void
  onTokenMouseEnter: (tokenIndex: number) => void
}

function Paragraphs({
  tokens,
  activeToken,
  selectionRange,
  onTokenClick,
  onTokenMouseDown,
  onTokenMouseEnter,
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
        <p key={pi} className="leading-9 text-lg text-zinc-200">
          {paraTokens.map(({ token, idx }, i) => {
            const isHighlighted =
              selectionRange !== null &&
              idx >= selectionRange[0] &&
              idx <= selectionRange[1]
            // Insert a space before this token unless it's the first token,
            // it's closing punctuation (comma, period, etc.), or the previous
            // token is opening punctuation (parenthesis, etc.).
            const prevW = paraTokens[i - 1]?.token.w ?? ""
            const isClosingPunct = /^[.,!?;:)\]»…\-—–]/.test(token.w)
            const prevIsOpeningPunct = /^[(\[«]$/.test(prevW)
            const spaceBefore = i > 0 && !isClosingPunct && !prevIsOpeningPunct
            return (
              <Fragment key={`${pi}-${token.si}-${i}`}>
                {spaceBefore && " "}
                <WordToken
                  token={token}
                  tokenIndex={idx}
                  isActive={activeToken?.w === token.w && activeToken?.si === token.si}
                  isHighlighted={isHighlighted}
                  onClick={onTokenClick}
                  onMouseDown={onTokenMouseDown}
                  onMouseEnter={onTokenMouseEnter}
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
  onPageChange: (page: number) => void
}

export function ReadingPane({ bookId, page, totalPages, onPageChange }: ReadingPaneProps) {
  const { activeToken, setActiveToken, setSelectedText } = useReaderStore()

  // Drag selection state — stored in refs to avoid re-renders during drag
  const dragRef = useRef<{ active: boolean; startIdx: number; endIdx: number }>({
    active: false,
    startIdx: -1,
    endIdx: -1,
  })
  const hasDraggedRef = useRef(false)
  // Visible highlight range (state so React re-renders the tokens)
  const [selectionRange, setSelectionRange] = useState<[number, number] | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["book-pages", bookId, page],
    queryFn: () => getBookPages(bookId, page, 1),
    placeholderData: (prev) => prev,
    refetchInterval: (query) =>
      query.state.data?.items[0]?.status === "pending" ? 3000 : false,
  })

  const currentPage = data?.items[0]

  function handleTokenMouseDown(tokenIndex: number) {
    if (!activeToken) return  // only track drag when panel is open
    dragRef.current = { active: true, startIdx: tokenIndex, endIdx: tokenIndex }
    hasDraggedRef.current = false
    setSelectionRange(null)
  }

  function handleTokenMouseEnter(tokenIndex: number) {
    if (!dragRef.current.active) return
    dragRef.current.endIdx = tokenIndex
    hasDraggedRef.current = true
    const lo = Math.min(dragRef.current.startIdx, dragRef.current.endIdx)
    const hi = Math.max(dragRef.current.startIdx, dragRef.current.endIdx)
    setSelectionRange([lo, hi])
  }

  function handleMouseUp() {
    if (!dragRef.current.active) return
    const didDrag = hasDraggedRef.current

    const lo = Math.min(dragRef.current.startIdx, dragRef.current.endIdx)
    const hi = Math.max(dragRef.current.startIdx, dragRef.current.endIdx)

    dragRef.current.active = false
    hasDraggedRef.current = false

    if (!didDrag || !activeToken || !currentPage) {
      setSelectionRange(null)
      return
    }

    // Collect text from the selected token range
    const selectedTokens = currentPage.tokens.slice(lo, hi + 1)
    const text = selectedTokens.map((t) => t.w).join(" ").trim()

    if (text.split(/\s+/).filter(Boolean).length < 2) {
      setSelectionRange(null)
      return
    }

    setSelectedText(text.slice(0, MAX_SELECTION_CHARS * 2), selectedTokens)
  }

  function handleTokenClick(token: TokenWithStatus) {
    // If we just finished a drag, ignore the click that fires after mouseup
    if (hasDraggedRef.current) {
      hasDraggedRef.current = false
      return
    }

    setSelectedText(null)
    setSelectionRange(null)

    if (activeToken?.w === token.w && activeToken?.si === token.si) {
      setActiveToken(null)
    } else {
      setActiveToken(token)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div
        // Disable browser text selection when panel is open so our token-based
        // drag selection takes over cleanly
        className={`flex-1 overflow-y-auto px-12 py-8${activeToken ? " select-none" : ""}`}
        onMouseUp={handleMouseUp}
        onDragStart={(e) => e.preventDefault()}
      >
        {isLoading ? (
          <div className="animate-pulse space-y-3">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="h-5 rounded bg-zinc-800" style={{ width: `${70 + (i % 3) * 10}%` }} />
            ))}
          </div>
        ) : currentPage ? (
          <div className="mx-auto max-w-2xl">
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
                onTokenClick={handleTokenClick}
                onTokenMouseDown={handleTokenMouseDown}
                onTokenMouseEnter={handleTokenMouseEnter}
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
        <span className="text-sm text-zinc-500">Page {page} of {totalPages}</span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= totalPages}
          className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-100 disabled:opacity-30"
        >
          Next
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
