"use client"

import { useEffect, useState } from "react"
import { cn } from "@/src/lib/cn"
import type { DrillQuestion } from "@/src/lib/api/grammar-drills"

interface Props {
  question: DrillQuestion
  onAnswer: (answer: string) => void
  disabled?: boolean
}

export function CaseIdentificationQuestion({ question, onAnswer, disabled = false }: Props) {
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    setSelected(null)
  }, [question.id])

  function handleSelect(option: string) {
    if (selected || disabled) return
    setSelected(option)
    onAnswer(option)
  }

  const options = question.options ?? []
  const sentence = question.sentence ?? ""
  const highlighted = question.highlighted_word ?? ""

  // Split sentence around the highlighted word (first occurrence)
  const idx = highlighted ? sentence.indexOf(highlighted) : -1
  const before = idx >= 0 ? sentence.slice(0, idx) : sentence
  const after = idx >= 0 ? sentence.slice(idx + highlighted.length) : ""

  return (
    <div className="space-y-6">
      <div>
        <p className="text-2xl font-bold text-zinc-100 mb-1">{question.display_lemma}</p>
        <p className="text-sm text-zinc-400">{question.prompt}</p>
      </div>

      {sentence && (
        <div className="rounded-lg bg-zinc-800 px-4 py-3 text-zinc-200 text-base leading-relaxed">
          {before}
          <span className="font-bold text-blue-300 underline underline-offset-4">
            {highlighted}
          </span>
          {after}
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {options.map((option) => {
          const isSelected = selected === option
          const isCorrect = option === question.correct_form
          const showFeedback = selected !== null

          return (
            <button
              key={option}
              onClick={() => handleSelect(option)}
              disabled={!!selected || disabled}
              className={cn(
                "min-h-[3rem] rounded-lg border px-4 py-3 text-sm font-medium transition-colors text-left",
                "disabled:cursor-default",
                !showFeedback && "border-zinc-700 bg-zinc-800 text-zinc-200 hover:border-zinc-500 hover:bg-zinc-700",
                showFeedback && isCorrect && "border-green-500 bg-green-500/10 text-green-300",
                showFeedback && isSelected && !isCorrect && "border-red-500 bg-red-500/10 text-red-300",
                showFeedback && !isSelected && !isCorrect && "border-zinc-700 bg-zinc-800 text-zinc-500"
              )}
            >
              {option}
            </button>
          )
        })}
      </div>
    </div>
  )
}
