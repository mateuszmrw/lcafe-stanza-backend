"use client"

import { AlertTriangle } from "lucide-react"
import type { CognateResult } from "@/src/lib/api/vocabulary"

interface CognateSectionProps {
  data: CognateResult | undefined
}

export function CognateSection({ data }: CognateSectionProps) {
  if (!data || !data.cognate_type) return null

  if (data.cognate_type === "false_friend") {
    return (
      <div className="rounded-lg border border-red-800/60 bg-red-950/30 p-2.5">
        <div className="flex items-center gap-1.5 mb-1">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-red-400" />
          <span className="text-xs font-semibold text-red-400">False friend</span>
        </div>
        {data.l1_lemma && (
          <p className="text-xs text-red-300 font-medium">
            {data.l2_meaning ?? "?"} ≠ {data.l1_lemma}
          </p>
        )}
        {(data.l2_meaning || data.l1_meaning) && (
          <p className="text-xs text-zinc-400 mt-0.5">
            {data.l2_meaning && <span>L2: {data.l2_meaning}</span>}
            {data.l2_meaning && data.l1_meaning && <span className="mx-1 text-zinc-600">·</span>}
            {data.l1_meaning && <span>L1: {data.l1_meaning}</span>}
          </p>
        )}
      </div>
    )
  }

  const pct = data.similarity_score != null
    ? Math.round(data.similarity_score * 100)
    : null

  const typeLabel =
    data.cognate_type === "partial" ? "Partial cognate"
    : data.cognate_type === "borrowing" ? "Loanword"
    : "Cognate"

  return (
    <div className="flex items-center gap-2">
      <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-600/20 px-2.5 py-1 text-xs font-medium text-amber-300 ring-1 ring-amber-600/40">
        ~ {data.l1_lemma}
        {pct != null && <span className="text-amber-500">{pct}%</span>}
      </span>
      <span className="text-xs text-zinc-600">{typeLabel}</span>
    </div>
  )
}
