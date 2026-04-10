"use client"

import type { TokenWithStatus } from "@/src/lib/api/books"
import { cn } from "@/src/lib/cn"

const STATUS_CLASSES: Record<string, string> = {
  new: "bg-blue-500/20 text-blue-200 cursor-pointer hover:bg-blue-500/40",
  learning: "bg-yellow-500/20 text-yellow-200 cursor-pointer hover:bg-yellow-500/40",
  known: "text-zinc-200 cursor-pointer hover:bg-zinc-700/50",
  well_known: "text-zinc-400 cursor-pointer hover:bg-zinc-700/50",
  ignored: "text-zinc-600 cursor-pointer hover:bg-zinc-700/30",
}

const NON_WORD_POS = new Set(["PUNCT", "SPACE", "SYM"])

interface WordTokenProps {
  token: TokenWithStatus
  tokenIndex: number
  isActive: boolean
  isHighlighted: boolean
  onClick: (token: TokenWithStatus) => void
  onMouseDown: (tokenIndex: number) => void
  onMouseEnter: (tokenIndex: number) => void
}

export function WordToken({
  token,
  tokenIndex,
  isActive,
  isHighlighted,
  onClick,
  onMouseDown,
  onMouseEnter,
}: WordTokenProps) {
  const isWord = !NON_WORD_POS.has(token.pos) && token.w.trim().length > 0

  if (!isWord) {
    return <span className="text-zinc-300">{token.w}</span>
  }

  return (
    <span
      role="button"
      tabIndex={0}
      onClick={() => onClick(token)}
      onMouseDown={() => onMouseDown(tokenIndex)}
      onMouseEnter={() => onMouseEnter(tokenIndex)}
      onKeyDown={(e) => e.key === "Enter" && onClick(token)}
      className={cn(
        "inline-block rounded text-base leading-relaxed transition-colors",
        STATUS_CLASSES[token.status] ?? STATUS_CLASSES.new,
        isActive && "ring-2 ring-blue-400 ring-offset-1 ring-offset-zinc-950",
        isHighlighted && "bg-blue-400/25 ring-1 ring-inset ring-blue-300/60",
      )}
    >
      {token.w}
    </span>
  )
}
