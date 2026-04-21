"use client"

import { useEffect, useRef, useState } from "react"
import { cn } from "@/src/lib/cn"
import type { DrillQuestion } from "@/src/lib/api/grammar-drills"

interface Props {
  question: DrillQuestion
  onAnswer: (answer: string) => void
  disabled?: boolean
}

export function FillBlankQuestion({ question, onAnswer, disabled = false }: Props) {
  const [value, setValue] = useState("")
  const [submitted, setSubmitted] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    setValue("")
    setSubmitted(false)
    inputRef.current?.focus()
  }, [question.id])

  function handleSubmit(e: React.SyntheticEvent) {
    e.preventDefault()
    if (!value.trim() || submitted || disabled) return
    setSubmitted(true)
    onAnswer(value.trim())
  }

  const sentence = question.sentence ?? ""
  const parts = sentence.split("___")

  return (
    <div className="space-y-6">
      <div>
        <p className="text-2xl font-bold text-zinc-100 mb-1">{question.display_lemma}</p>
        <p className="text-sm text-zinc-400">{question.prompt}</p>
      </div>

      {parts.length >= 2 && (
        <div className="rounded-lg bg-zinc-800 px-4 py-3 text-zinc-200 text-base leading-relaxed">
          {parts[0]}
          <span className="inline-block min-w-[3rem] border-b-2 border-blue-400 text-blue-400 text-center px-1">
            {submitted ? value : "___"}
          </span>
          {parts[1]}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-3">
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={submitted || disabled}
          placeholder="Type the correct form…"
          className={cn(
            "w-full rounded-lg border bg-zinc-800 px-4 py-3 text-zinc-100",
            "placeholder:text-zinc-500 focus:outline-none focus:ring-2 focus:ring-blue-500",
            "disabled:opacity-50",
            submitted ? "border-zinc-600" : "border-zinc-700"
          )}
        />
        {!submitted && (
          <button
            type="submit"
            disabled={!value.trim() || disabled}
            className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white
              hover:bg-blue-500 disabled:opacity-40 transition-colors"
          >
            Check
          </button>
        )}
      </form>
    </div>
  )
}
