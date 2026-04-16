"use client"

import type { TokenWithStatus } from "@/src/lib/api/books"
import { cn } from "@/src/lib/cn"
import { getTokenClass } from "@/src/lib/status-colors"

const NON_WORD_POS = new Set(["PUNCT", "SPACE", "SYM"])

interface WordTokenProps {
  token: TokenWithStatus
  tokenIndex: number
  isActive: boolean
  isHighlighted: boolean
  isAudioActive?: boolean
  isPhraseToken?: boolean
  onClick: (token: TokenWithStatus, e: React.MouseEvent<HTMLSpanElement>) => void
}

export function WordToken({
  token,
  tokenIndex,
  isActive,
  isHighlighted,
  isAudioActive,
  isPhraseToken,
  onClick,
}: WordTokenProps) {
  const isWord = !NON_WORD_POS.has(token.pos) && token.w.trim().length > 0

  if (!isWord) {
    return (
      <span
        className={cn(
          "text-zinc-300",
          isAudioActive && "underline decoration-amber-400 decoration-2 underline-offset-2"
        )}
      >
        {token.w}
      </span>
    )
  }

  // Show the lemma on hover when it differs from the surface form — useful
  // for inflected languages where the dictionary form isn't obvious.
  const hoverTitle = token.l && token.l !== token.w ? token.l : undefined

  return (
    <span
      role="button"
      tabIndex={0}
      data-token-index={tokenIndex}
      title={hoverTitle}
      onClick={(e) => onClick(token, e)}
      onKeyDown={(e) => e.key === "Enter" && onClick(token, e as unknown as React.MouseEvent<HTMLSpanElement>)}
      className={cn(
        "inline-flex flex-col items-center rounded text-base leading-relaxed transition-colors",
        getTokenClass(token.status, token.d),
        isActive && "ring-2 ring-blue-400 ring-offset-1 ring-offset-zinc-950",
        isHighlighted && "bg-blue-400/25 ring-1 ring-inset ring-blue-300/60",
        isPhraseToken && !isHighlighted && "bg-emerald-500/30",
        isAudioActive && "underline decoration-amber-400 decoration-2 underline-offset-2",
      )}
    >
      {token.w}
      {token.hint && (
        <span className="text-[0.6rem] leading-none text-zinc-400 font-normal not-italic max-w-[6rem] truncate">
          {token.hint}
        </span>
      )}
    </span>
  )
}
