"use client"

import type { TokenWithStatus } from "@/src/lib/api/books"
import type { CognateData } from "@/src/lib/api/vocabulary"
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
  isCorefHighlighted?: boolean
  cognateData?: CognateData
  onClick: (token: TokenWithStatus, e: React.MouseEvent<HTMLSpanElement>) => void
  onHoverChain?: (chainId: number | null) => void
}

export function WordToken({
  token,
  tokenIndex,
  isActive,
  isHighlighted,
  isAudioActive,
  isPhraseToken,
  isCorefHighlighted,
  cognateData,
  onClick,
  onHoverChain,
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

  const hoverTitle = cognateData
    ? cognateData.cognate_type === "false_friend"
      ? `⚠ False friend: ${token.w} ≠ ${cognateData.l1_lemma ?? ""}${cognateData.l2_meaning ? ` (means "${cognateData.l2_meaning}")` : ""}`
      : `≈ ${cognateData.l1_lemma ?? ""}${cognateData.l1_meaning ? ` — ${cognateData.l1_meaning}` : ""}`
    : token.l && token.l !== token.w ? token.l : undefined

  return (
    <span
      role="button"
      tabIndex={0}
      data-token-index={tokenIndex}
      title={hoverTitle}
      onClick={(e) => onClick(token, e)}
      onKeyDown={(e) => e.key === "Enter" && onClick(token, e as unknown as React.MouseEvent<HTMLSpanElement>)}
      onMouseEnter={() => token.cc && token.cc > 0 ? onHoverChain?.(token.cc) : undefined}
      onMouseLeave={() => onHoverChain?.(null)}
      className={cn(
        "inline-flex flex-col items-center text-base leading-relaxed transition-colors",
        isHighlighted
          ? "bg-violet-500/40 text-zinc-100"
          : cn("rounded", getTokenClass(token.status, token.d)),
        !isHighlighted && isActive && "ring-2 ring-blue-400 ring-offset-1 ring-offset-zinc-950",
        !isHighlighted && isPhraseToken && "bg-emerald-500/30",
        !isHighlighted && isCorefHighlighted && "bg-sky-900/40 ring-1 ring-sky-400/50",
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
