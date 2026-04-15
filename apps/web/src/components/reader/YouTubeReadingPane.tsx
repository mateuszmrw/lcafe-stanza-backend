"use client"

import { Fragment, useEffect, useRef } from "react"
import { useQuery } from "@tanstack/react-query"
import type { TokenWithStatus, PageResponse } from "@/src/lib/api/books"
import { getBookPages } from "@/src/lib/api/books"
import { useReaderStore } from "@/src/stores/reader"
import { useAudioPlayerStore } from "@/src/stores/audioPlayer"
import { useReaderSettings, FONT_SIZE_CLASS } from "@/src/stores/readerSettings"
import { sentenceText } from "@/src/lib/sentences"
import { WordToken } from "./WordToken"

function isNoSpaceLanguage(code: string): boolean {
  return code.startsWith("zh") || code === "ja"
}

interface YouTubeReadingPaneProps {
  bookId: string
  totalPages: number
  languageCode: string
}

interface SentenceEntry {
  pageNumber: number
  sentenceIndex: number
  tokens: { token: TokenWithStatus; idx: number }[]
}

/** Build a flat list of sentences across all pages, preserving a global token index. */
function buildSentences(pages: PageResponse[]): SentenceEntry[] {
  const sentences: SentenceEntry[] = []
  let globalIdx = 0
  for (const page of pages) {
    const bysi = new Map<number, { token: TokenWithStatus; idx: number }[]>()
    for (const token of page.tokens) {
      if (!bysi.has(token.si)) bysi.set(token.si, [])
      bysi.get(token.si)!.push({ token, idx: globalIdx++ })
    }
    for (const [si, tokens] of bysi) {
      sentences.push({ pageNumber: page.page_number, sentenceIndex: si, tokens })
    }
  }
  return sentences
}

export function YouTubeReadingPane({ bookId, totalPages, languageCode }: YouTubeReadingPaneProps) {
  const noWordSpacing = isNoSpaceLanguage(languageCode)
  const { activeToken, setActiveToken, setPanelAnchor, setSentenceContext } = useReaderStore()
  const { activeSentenceIndex, lastPageNumber, seekTo, timeIndex } = useAudioPlayerStore()
  const { fontSize } = useReaderSettings()

  const sentenceRefs = useRef<Map<string, HTMLDivElement>>(new Map())
  const containerRef = useRef<HTMLDivElement>(null)

  // Fetch ALL pages at once (YouTube videos typically have ~20 pages)
  const { data, isLoading } = useQuery({
    queryKey: ["book-all-pages", bookId],
    queryFn: () => getBookPages(bookId, 1, totalPages),
    staleTime: Infinity,
  })

  const pages = data?.items ?? []
  const sentences = pages.length > 0 ? buildSentences(pages) : []

  // Auto-scroll to active sentence (Spotify-style)
  useEffect(() => {
    if (activeSentenceIndex === null || lastPageNumber === null) return
    const key = `${lastPageNumber}-${activeSentenceIndex}`
    const el = sentenceRefs.current.get(key)
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" })
    }
  }, [activeSentenceIndex, lastPageNumber])

  function handleSentenceClick(pageNumber: number, sentenceIndex: number) {
    const entry = timeIndex.find(
      (e) => e.page_number === pageNumber && e.sentence_index === sentenceIndex
    )
    if (entry) {
      seekTo(entry.start_ms)
    }
  }

  function handleTokenClick(token: TokenWithStatus, e: React.MouseEvent<HTMLSpanElement>, page: PageResponse) {
    if (activeToken?.w === token.w && activeToken?.si === token.si) {
      setActiveToken(null)
      setPanelAnchor(null)
      setSentenceContext(null)
    } else {
      setActiveToken(token)
      const rect = e.currentTarget.getBoundingClientRect()
      setPanelAnchor({ x: rect.left + rect.width / 2, top: rect.top, bottom: rect.bottom })
      const sentenceTokens = page.tokens.filter((t) => t.si === token.si)
      setSentenceContext(sentenceText(sentenceTokens, noWordSpacing), sentenceTokens)
    }

    // Also seek the video
    handleSentenceClick(page.page_number, token.si)
  }

  const isActive = (pageNumber: number, si: number) =>
    lastPageNumber === pageNumber && activeSentenceIndex === si

  if (isLoading) {
    return (
      <div className="flex-1 overflow-y-auto px-8 py-6">
        <div className="mx-auto max-w-2xl animate-pulse space-y-4">
          {Array.from({ length: 12 }).map((_, i) => (
            <div key={i} className="h-5 rounded bg-zinc-800" style={{ width: `${60 + (i % 4) * 10}%` }} />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div ref={containerRef} className="flex-1 overflow-y-auto px-6 py-4">
      <div className="mx-auto max-w-xl">
        {sentences.map((sentence) => {
          const key = `${sentence.pageNumber}-${sentence.sentenceIndex}`
          const active = isActive(sentence.pageNumber, sentence.sentenceIndex)
          const page = pages.find((p) => p.page_number === sentence.pageNumber)!

          return (
            <div
              key={key}
              ref={(el) => {
                if (el) sentenceRefs.current.set(key, el)
                else sentenceRefs.current.delete(key)
              }}
              onClick={() => handleSentenceClick(sentence.pageNumber, sentence.sentenceIndex)}
              className={`cursor-pointer rounded-md px-3 py-1 transition-colors duration-200 ${
                active
                  ? "bg-zinc-800/60"
                  : "hover:bg-zinc-800/30 opacity-40"
              }`}
            >
              <p className={`leading-relaxed ${FONT_SIZE_CLASS[fontSize]} ${
                active ? "text-zinc-100 font-medium" : "text-zinc-500"
              }`}>
                {sentence.tokens.map(({ token, idx }, i) => {
                  const prevW = sentence.tokens[i - 1]?.token.w ?? ""
                  const isClosingPunct = /^[.,!?;:)\]»…\-—–。，！？；：」』]/.test(token.w)
                  const prevIsOpening = /^[(\[«「『]$/.test(prevW)
                  const spaceBefore = !noWordSpacing && i > 0 && !isClosingPunct && !prevIsOpening

                  return (
                    <Fragment key={`${key}-${i}`}>
                      {spaceBefore && " "}
                      <WordToken
                        token={token}
                        tokenIndex={idx}
                        isActive={activeToken?.w === token.w && activeToken?.si === token.si}
                        isHighlighted={false}
                        isAudioActive={active}
                        onClick={(t, e) => handleTokenClick(t, e, page)}
                      />
                    </Fragment>
                  )
                })}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}
