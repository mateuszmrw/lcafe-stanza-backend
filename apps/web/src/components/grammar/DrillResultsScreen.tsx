"use client"

import { CheckCircle, XCircle } from "lucide-react"
import { cn } from "@/src/lib/cn"
import type { DrillSubmitResponse } from "@/src/lib/api/grammar-drills"

interface Props {
  sessionResponse: DrillSubmitResponse
  onTryAgain: () => void
  onBackToLibrary: () => void
  tryAgainLabel?: string
}

export function DrillResultsScreen({ sessionResponse, onTryAgain, onBackToLibrary, tryAgainLabel = "Try again" }: Props) {
  const { score, total, results } = sessionResponse
  const pct = total > 0 ? Math.round((score / total) * 100) : 0

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <p className="text-sm font-medium text-zinc-400 uppercase tracking-widest">Session complete</p>
        <p
          className={cn(
            "text-5xl font-bold",
            pct >= 80 ? "text-green-400" : pct >= 50 ? "text-yellow-400" : "text-red-400"
          )}
        >
          {score} / {total}
        </p>
        <p className="text-zinc-400">{pct}% correct</p>
      </div>

      <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
        {results.map((r) => (
          <div
            key={r.question_id}
            className={cn(
              "flex items-start gap-3 rounded-lg px-4 py-3",
              r.correct ? "bg-green-500/10" : "bg-red-500/10"
            )}
          >
            {r.correct ? (
              <CheckCircle className="h-4 w-4 mt-0.5 shrink-0 text-green-400" />
            ) : (
              <XCircle className="h-4 w-4 mt-0.5 shrink-0 text-red-400" />
            )}
            <div className="min-w-0 text-sm">
              <span className="font-medium text-zinc-200">{r.lemma}</span>
              <span className="text-zinc-500 mx-1">·</span>
              <span className="text-zinc-400">{r.form_type}</span>
              {!r.correct && (
                <p className="text-zinc-400 mt-0.5">
                  You wrote:{" "}
                  <span className="text-red-300">{r.user_answer || "(blank)"}</span>
                  {" · "}
                  Correct:{" "}
                  <span className="text-green-300">{r.correct_form}</span>
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-3">
        <button
          onClick={onTryAgain}
          className="flex-1 rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white
            hover:bg-blue-500 transition-colors"
        >
          {tryAgainLabel}
        </button>
        <button
          onClick={onBackToLibrary}
          className="flex-1 rounded-lg border border-zinc-700 px-4 py-3 text-sm font-medium
            text-zinc-300 hover:bg-zinc-800 transition-colors"
        >
          Back to library
        </button>
      </div>
    </div>
  )
}
