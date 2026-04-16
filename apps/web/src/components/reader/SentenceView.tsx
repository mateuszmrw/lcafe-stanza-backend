"use client"

import { Fragment, useEffect, useRef, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { ChevronLeft, ChevronRight, Languages, Bookmark, BookmarkCheck } from "lucide-react"
import type { TokenWithStatus } from "@/src/lib/api/books"
import { translate } from "@/src/lib/api/translation"
import { sentenceText } from "@/src/lib/sentences"
import { saveSentence, listSentences, deleteSentence } from "@/src/lib/api/sentences"
import { useAudioPlayerStore } from "@/src/stores/audioPlayer"
import { WordToken } from "./WordToken"

function isNoSpaceLanguage(code: string): boolean {
  return code.startsWith("zh") || code === "ja"
}

interface SentenceViewProps {
  sentences: TokenWithStatus[][]
  currentIndex: number
  totalPages: number
  page: number
  languageCode: string
  languageId: number
  bookId: string
  activeToken: TokenWithStatus | null
  onAdvance: () => void
  onBack: () => void
  onNextPage: () => void
  onPrevPage: () => void
  onTokenClick: (token: TokenWithStatus, e: React.MouseEvent<HTMLSpanElement>) => void
}

export function SentenceView({
  sentences,
  currentIndex,
  totalPages,
  page,
  languageCode,
  languageId,
  bookId,
  activeToken,
  onAdvance,
  onBack,
  onNextPage,
  onPrevPage,
  onTokenClick,
}: SentenceViewProps) {
  const noWordSpacing = isNoSpaceLanguage(languageCode)
  const [showTranslation, setShowTranslation] = useState(false)
  // Per-field selectors — audio player ticks 5x/sec, don't re-render on currentTimeMs.
  const isPlaying = useAudioPlayerStore((s) => s.isPlaying)
  const activeSentenceIndex = useAudioPlayerStore((s) => s.activeSentenceIndex)
  const prevAudioSiRef = useRef<number | null>(null)
  const queryClient = useQueryClient()

  const currentSentence = sentences[currentIndex] ?? []
  const text = sentenceText(currentSentence, noWordSpacing)

  // Reset translation visibility on sentence change
  useEffect(() => {
    setShowTranslation(false)
  }, [currentIndex])

  // Auto-advance sentence index when audio plays
  useEffect(() => {
    if (!isPlaying || activeSentenceIndex === null) return
    if (activeSentenceIndex === prevAudioSiRef.current) return
    prevAudioSiRef.current = activeSentenceIndex

    // Find sentence in current page matching the audio's active sentence_index
    const matchingIdx = sentences.findIndex(
      (tokens) => tokens.length > 0 && tokens[0].si === activeSentenceIndex
    )
    if (matchingIdx !== -1 && matchingIdx !== currentIndex) {
      onAdvance()
    }
  }, [isPlaying, activeSentenceIndex, sentences, currentIndex, onAdvance])

  const { data: translationData, isLoading: translationLoading } = useQuery({
    queryKey: ["sentence-translation", text, languageCode],
    queryFn: () => translate(text, languageCode),
    enabled: showTranslation && text.length > 0,
    staleTime: Infinity,
  })

  const currentSi = currentSentence[0]?.si ?? currentIndex

  const { data: savedSentences } = useQuery({
    queryKey: ["saved-sentences", languageId],
    queryFn: () => listSentences(languageId),
    staleTime: 30_000,
  })

  const savedSet = new Set((savedSentences ?? []).map((s) => s.sentence_index))
  const savedById = new Map((savedSentences ?? []).map((s) => [s.sentence_index, s.id]))
  const isSaved = savedSet.has(currentSi)

  const saveMutation = useMutation({
    mutationFn: () => saveSentence({ language_id: languageId, sentence_text: text, sentence_index: currentSi, book_id: bookId }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-sentences", languageId] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteSentence(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["saved-sentences", languageId] }),
  })

  const translation =
    translationData?.results.flatMap((r) => r.translated_texts).join(" / ") ?? null

  // Keyboard navigation
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return
      if (e.key === "ArrowRight" || e.key === " ") {
        e.preventDefault()
        if (currentIndex >= sentences.length - 1) {
          onNextPage()
        } else {
          onAdvance()
        }
      } else if (e.key === "ArrowLeft") {
        e.preventDefault()
        if (currentIndex <= 0) {
          onPrevPage()
        } else {
          onBack()
        }
      }
    }
    document.addEventListener("keydown", handleKey)
    return () => document.removeEventListener("keydown", handleKey)
  }, [currentIndex, sentences.length, onAdvance, onBack, onNextPage, onPrevPage])

  // Render tokens for the current sentence
  const renderTokens = () => {
    const tokens = currentSentence
    return (
      <p className="leading-10 text-xl text-zinc-200">
        {tokens.map((token, i) => {
          const prevW = tokens[i - 1]?.w ?? ""
          const isClosingPunct = /^[.,!?;:)\]»…\-—–。，！？；：」』]/.test(token.w)
          const prevIsOpeningPunct = /^[(\[«「『]$/.test(prevW)
          const spaceBefore = !noWordSpacing && i > 0 && !isClosingPunct && !prevIsOpeningPunct
          return (
            <Fragment key={`${token.si}-${i}`}>
              {spaceBefore && " "}
              <WordToken
                token={token}
                tokenIndex={i}
                isActive={activeToken?.w === token.w && activeToken?.si === token.si}
                isHighlighted={false}
                isAudioActive={isPlaying && activeSentenceIndex !== null && token.si === activeSentenceIndex}
                onClick={onTokenClick}
              />
            </Fragment>
          )
        })}
      </p>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* Progress */}
      <div className="flex items-center justify-between border-b border-zinc-800 px-8 py-2 text-xs text-zinc-500">
        <span>
          Page {page} of {totalPages}
        </span>
        <span>
          Sentence {currentIndex + 1} of {sentences.length}
        </span>
      </div>

      {/* Sentence content */}
      <div className="flex flex-1 flex-col items-center justify-center gap-6 overflow-y-auto px-12 py-8">
        <div className="mx-auto w-full max-w-2xl text-center">
          {renderTokens()}
        </div>

        {/* Save sentence */}
        <div className="flex justify-center">
          {isSaved ? (
            <button
              onClick={() => { const id = savedById.get(currentSi); if (id) deleteMutation.mutate(id) }}
              className="flex items-center gap-1 text-xs text-amber-400 hover:text-amber-300 transition"
              title="Remove saved sentence"
            >
              <BookmarkCheck className="h-3.5 w-3.5" /> Saved
            </button>
          ) : (
            <button
              onClick={() => saveMutation.mutate()}
              className="flex items-center gap-1 text-xs text-zinc-600 hover:text-zinc-400 transition"
              title="Save sentence"
            >
              <Bookmark className="h-3.5 w-3.5" /> Save sentence
            </button>
          )}
        </div>

        {/* Translation strip */}
        <div className="flex flex-col items-center gap-2">
          {showTranslation ? (
            translationLoading ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-700 border-t-blue-500" />
            ) : translation ? (
              <p className="max-w-xl text-center text-sm text-zinc-400">{translation}</p>
            ) : (
              <p className="text-xs text-zinc-600">No translation available</p>
            )
          ) : (
            <button
              onClick={() => setShowTranslation(true)}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-zinc-500 transition hover:bg-zinc-800 hover:text-zinc-300"
            >
              <Languages className="h-3.5 w-3.5" />
              Show translation
            </button>
          )}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex items-center justify-between border-t border-zinc-800 px-8 py-4">
        <button
          onClick={() => {
            if (currentIndex <= 0) onPrevPage()
            else onBack()
          }}
          disabled={currentIndex <= 0 && page <= 1}
          className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-100 disabled:opacity-30"
        >
          <ChevronLeft className="h-4 w-4" />
          {currentIndex <= 0 ? "Prev page" : "Previous"}
        </button>

        <button
          onClick={() => {
            if (currentIndex >= sentences.length - 1) onNextPage()
            else onAdvance()
          }}
          disabled={currentIndex >= sentences.length - 1 && page >= totalPages}
          className="flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm text-zinc-400 transition hover:bg-zinc-800 hover:text-zinc-100 disabled:opacity-30"
        >
          {currentIndex >= sentences.length - 1 ? "Next page" : "Next"}
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
