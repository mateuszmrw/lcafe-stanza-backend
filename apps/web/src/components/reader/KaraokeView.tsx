"use client"

import { Fragment, useEffect, useRef } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Bookmark, BookmarkCheck } from "lucide-react"
import type { TokenWithStatus } from "@/src/lib/api/books"
import { getBookPages } from "@/src/lib/api/books"
import { useReaderStore } from "@/src/stores/reader"
import { useAudioPlayerStore } from "@/src/stores/audioPlayer"
import { groupBySentence, sentenceText } from "@/src/lib/sentences"
import { saveSentence, listSentences, deleteSentence } from "@/src/lib/api/sentences"
import { WordToken } from "./WordToken"
import { cn } from "@/src/lib/cn"

const PUNCT_RE = /^[.,!?;:)\]»…\-—–。，！？；：」』]/
const OPEN_PUNCT_RE = /^[(\[«「『]$/

function isNoSpaceLanguage(code: string): boolean {
  return code.startsWith("zh") || code === "ja"
}

interface KaraokeViewProps {
  bookId: string
  page: number
  languageCode: string
  languageId: number
}

export function KaraokeView({ bookId, page, languageCode, languageId }: KaraokeViewProps) {
  const noSpace = isNoSpaceLanguage(languageCode)
  const { activeToken, setActiveToken, setPanelAnchor } = useReaderStore()
  const { activeSentenceIndex, seekToSentence, seekTo } = useAudioPlayerStore()
  const queryClient = useQueryClient()

  const sentenceRefs = useRef<Map<number, HTMLDivElement>>(new Map())
  const containerRef = useRef<HTMLDivElement>(null)

  const { data } = useQuery({
    queryKey: ["book-pages", bookId, page],
    queryFn: () => getBookPages(bookId, page, 1),
    placeholderData: (prev) => prev,
  })

  const { data: savedSentences } = useQuery({
    queryKey: ["saved-sentences", languageId],
    queryFn: () => listSentences(languageId),
    staleTime: 30_000,
  })

  const saveMutation = useMutation({
    mutationFn: (vars: { si: number; text: string }) =>
      saveSentence({ language_id: languageId, sentence_text: vars.text, sentence_index: vars.si, book_id: bookId }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-sentences", languageId] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteSentence(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-sentences", languageId] }),
  })

  const tokens = data?.items[0]?.tokens ?? []
  const sentences = groupBySentence(tokens)

  // Build set of saved sentence indices for quick lookup
  const savedSet = new Set((savedSentences ?? []).map((s) => s.sentence_index))
  const savedById = new Map((savedSentences ?? []).map((s) => [s.sentence_index, s.id]))

  // Index of the sentence currently playing within this page's sentence list
  const activeSentIdx = activeSentenceIndex !== null
    ? sentences.findIndex((s) => s.length > 0 && s[0].si === activeSentenceIndex)
    : -1

  // Scroll active sentence to center when it changes
  useEffect(() => {
    if (activeSentIdx === -1) return
    const el = sentenceRefs.current.get(activeSentIdx)
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" })
    }
  }, [activeSentIdx])

  function handleTokenClick(token: TokenWithStatus, e: React.MouseEvent<HTMLSpanElement>) {
    if (activeToken?.w === token.w && activeToken?.si === token.si) {
      setActiveToken(null)
      setPanelAnchor(null)
    } else {
      setActiveToken(token)
      const rect = e.currentTarget.getBoundingClientRect()
      setPanelAnchor({ x: rect.left + rect.width / 2, top: rect.top, bottom: rect.bottom })
    }
    const target = seekToSentence(token.si)
    if (target) seekTo(target.ms, target.audioFile)
  }

  function handleSentenceSeek(si: number) {
    const target = seekToSentence(si)
    if (target) seekTo(target.ms, target.audioFile)
  }

  return (
    <div ref={containerRef} className="h-full overflow-y-auto">
      {/* Top padding so first sentence can scroll to center */}
      <div className="h-[40vh]" />

      <div className="mx-auto max-w-2xl space-y-5 px-8 text-center">
        {sentences.map((sentenceTokens, idx) => {
          const si = sentenceTokens[0]?.si ?? idx
          const isActive = idx === activeSentIdx
          const isPast = activeSentIdx !== -1 && idx < activeSentIdx
          const isNear = activeSentIdx !== -1 && idx > activeSentIdx && idx <= activeSentIdx + 2

          return (
            <div
              key={si}
              ref={(el) => {
                if (el) sentenceRefs.current.set(idx, el)
                else sentenceRefs.current.delete(idx)
              }}
              className={cn(
                "transition-all duration-500",
                !isActive && "cursor-pointer"
              )}
              onClick={() => {
                if (!isActive) handleSentenceSeek(si)
              }}
            >
              <p
                className={cn(
                  "leading-relaxed transition-all duration-500",
                  isActive
                    ? "text-2xl font-medium text-zinc-100"
                    : isPast
                    ? "text-base text-zinc-600 hover:text-zinc-500"
                    : isNear
                    ? "text-lg text-zinc-400 hover:text-zinc-300"
                    : "text-base text-zinc-500 hover:text-zinc-400"
                )}
              >
                {sentenceTokens.map((token, i) => {
                  const prevW = sentenceTokens[i - 1]?.w ?? ""
                  const spaceBefore =
                    !noSpace &&
                    i > 0 &&
                    !PUNCT_RE.test(token.w) &&
                    !OPEN_PUNCT_RE.test(prevW)

                  if (isActive) {
                    return (
                      <Fragment key={`${si}-${i}`}>
                        {spaceBefore && " "}
                        <WordToken
                          token={token}
                          tokenIndex={i}
                          isActive={
                            activeToken?.w === token.w &&
                            activeToken?.si === token.si
                          }
                          isHighlighted={false}
                          isAudioActive={false}
                          onClick={handleTokenClick}
                        />
                      </Fragment>
                    )
                  }

                  return (
                    <Fragment key={`${si}-${i}`}>
                      {spaceBefore && " "}
                      <span
                        onClick={(e) => {
                          e.stopPropagation()
                          handleTokenClick(token, e as unknown as React.MouseEvent<HTMLSpanElement>)
                        }}
                      >
                        {token.w}
                      </span>
                    </Fragment>
                  )
                })}
              </p>
              {isActive && (
                <div className="mt-2 flex justify-center">
                  {savedSet.has(si) ? (
                    <button
                      onClick={(e) => { e.stopPropagation(); const id = savedById.get(si); if (id) deleteMutation.mutate(id) }}
                      className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition"
                      title="Remove saved sentence"
                    >
                      <BookmarkCheck className="h-3.5 w-3.5" /> Saved
                    </button>
                  ) : (
                    <button
                      onClick={(e) => { e.stopPropagation(); saveMutation.mutate({ si, text: sentenceText(sentenceTokens, noSpace) }) }}
                      className="flex items-center gap-1 text-xs text-zinc-600 hover:text-zinc-400 transition"
                      title="Save sentence"
                    >
                      <Bookmark className="h-3.5 w-3.5" /> Save
                    </button>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Bottom padding so last sentence can scroll to center */}
      <div className="h-[50vh]" />
    </div>
  )
}
