"use client"

import { useEffect, useState } from "react"
import { cn } from "@/src/lib/cn"
import type { DrillQuestion } from "@/src/lib/api/grammar-drills"

interface Props {
  question: DrillQuestion
  onAnswer: (answer: string) => void
  disabled?: boolean
}

export function MultipleChoiceQuestion({ question, onAnswer, disabled = false }: Props) {
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

  return (
    <div className="space-y-6">
      <div>
        <p className="text-2xl font-bold text-zinc-100 mb-1">{question.display_lemma}</p>
        <p className="text-sm text-zinc-400">{question.prompt}</p>
      </div>

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
