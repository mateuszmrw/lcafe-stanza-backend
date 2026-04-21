"use client"

interface ExercisePromptProps {
  candidateCount: number
  endOfContent: boolean
  onLetGo: () => void
  onSkip: () => void
}

export function ExercisePrompt({ candidateCount, endOfContent, onLetGo, onSkip }: ExercisePromptProps) {
  const wordLabel = `${candidateCount} word${candidateCount !== 1 ? "s" : ""}`

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onSkip}
    >
      <div
        className="relative w-full max-w-sm rounded-xl border border-zinc-700 bg-zinc-900 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-2 text-lg font-semibold text-zinc-100">
          {endOfContent ? "Great job finishing!" : "Quick practice"}
        </h2>
        <p className="mb-6 text-sm text-zinc-400">
          {endOfContent
            ? `Review ${wordLabel} before you go?`
            : `${wordLabel} to review. Ready?`}
        </p>
        <div className="flex gap-3">
          <button
            onClick={onLetGo}
            className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-blue-500"
          >
            Let&apos;s go
          </button>
          <button
            onClick={onSkip}
            className="flex-1 rounded-lg border border-zinc-700 px-4 py-2 text-sm font-medium text-zinc-300 transition hover:bg-zinc-800"
          >
            Skip for now
          </button>
        </div>
      </div>
    </div>
  )
}
