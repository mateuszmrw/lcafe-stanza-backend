"use client"

import { useRouter } from "next/navigation"
import { useCallback, useState } from "react"
import { FillBlankQuestion } from "./FillBlankQuestion"
import { MultipleChoiceQuestion } from "./MultipleChoiceQuestion"
import { CaseIdentificationQuestion } from "./CaseIdentificationQuestion"
import { DrillResultsScreen } from "./DrillResultsScreen"
import { getDrillSession, normalizeAnswer, submitDrillAnswers } from "@/src/lib/api/grammar-drills"
import type { DrillAnswer, DrillQuestion, DrillSessionResponse, DrillSessionType, DrillSubmitResponse } from "@/src/lib/api/grammar-drills"
import { CheckCircle, XCircle } from "lucide-react"
import { cn } from "@/src/lib/cn"

type State =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "drilling"; session: DrillSessionResponse; index: number; answers: DrillAnswer[]; lastAnswer: string | null }
  | { phase: "submitted_question"; session: DrillSessionResponse; index: number; answers: DrillAnswer[]; lastAnswer: string }
  | { phase: "results"; submitResponse: DrillSubmitResponse }
  | { phase: "error"; message: string }

const UNAVAILABLE_REASONS: Record<string, string> = {
  no_active_language: "Set an active language in Settings to unlock grammar drills.",
  no_form_data: "No dictionary form data available for your active language yet.",
  no_learning_words: "Add words to your learning list to unlock grammar drills.",
  no_drillable_words: "None of your learning words have dictionary form data yet.",
}

interface Props {
  drillType?: DrillSessionType
  onBack?: () => void
}

export function DrillSessionManager({ drillType = "form_production", onBack }: Props) {
  const router = useRouter()
  const [state, setState] = useState<State>({ phase: "idle" })

  const startSession = useCallback(async () => {
    setState({ phase: "loading" })
    try {
      const session = await getDrillSession(drillType)
      if (!session.available || !session.questions.length) {
        const reason = session.reason ?? "no_drillable_words"
        setState({
          phase: "error",
          message: UNAVAILABLE_REASONS[reason] ?? "No drillable words found.",
        })
        return
      }
      setState({ phase: "drilling", session, index: 0, answers: [], lastAnswer: null })
    } catch {
      setState({ phase: "error", message: "Could not load your drill session. Try again." })
    }
  }, [])

  const handleAnswer = useCallback(
    (answer: string) => {
      if (state.phase !== "drilling") return
      const { session, index, answers } = state
      const question = session.questions[index]
      const newAnswers = [...answers, { question_id: question.id, answer }]
      setState({
        phase: "submitted_question",
        session,
        index,
        answers: newAnswers,
        lastAnswer: answer,
      })
    },
    [state]
  )

  const handleNext = useCallback(async () => {
    if (state.phase !== "submitted_question") return
    const { session, index, answers } = state
    const nextIndex = index + 1

    if (nextIndex < session.questions.length) {
      setState({ phase: "drilling", session, index: nextIndex, answers, lastAnswer: null })
      return
    }

    // All questions answered — submit
    setState({ phase: "loading" })
    try {
      const submitResponse = await submitDrillAnswers(session.session_id, answers)
      setState({ phase: "results", submitResponse })
    } catch {
      setState({ phase: "error", message: "Could not submit your answers. Try again." })
    }
  }, [state])

  if (state.phase === "idle") {
    return (
      <div className="space-y-4 text-center">
        <button
          onClick={startSession}
          className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
        >
          Start session
        </button>
      </div>
    )
  }

  if (state.phase === "loading") {
    return (
      <div className="flex justify-center py-12">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
      </div>
    )
  }

  if (state.phase === "error") {
    return (
      <div className="space-y-4 text-center">
        <p className="text-zinc-400 text-sm">{state.message}</p>
        <button
          onClick={() => setState({ phase: "idle" })}
          className="rounded-lg border border-zinc-700 px-5 py-2.5 text-sm text-zinc-300 hover:bg-zinc-800 transition-colors"
        >
          Back
        </button>
      </div>
    )
  }

  if (state.phase === "results") {
    return (
      <DrillResultsScreen
        sessionResponse={state.submitResponse}
        onTryAgain={onBack ?? (() => setState({ phase: "idle" }))}
        onBackToLibrary={onBack ?? (() => router.push("/library"))}
        tryAgainLabel={onBack ? "Back to drills" : "Try again"}
      />
    )
  }

  // drilling or submitted_question
  const { session, index, lastAnswer } = state
  const isSubmitted = state.phase === "submitted_question"
  const question: DrillQuestion = session.questions[index]
  const total = session.questions.length

  const isCorrect =
    isSubmitted &&
    lastAnswer != null &&
    question.accepted_forms.some(
      (f) => normalizeAnswer(f) === normalizeAnswer(lastAnswer)
    )

  return (
    <div className="space-y-6">
      {/* Progress */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-300"
            style={{ width: `${((index + (isSubmitted ? 1 : 0)) / total) * 100}%` }}
          />
        </div>
        <span className="text-xs text-zinc-500 shrink-0">
          {index + 1} / {total}
        </span>
      </div>

      {/* Question */}
      <div className={cn("transition-opacity", isSubmitted && "opacity-60")}>
        {question.type === "fill_blank" ? (
          <FillBlankQuestion
            question={question}
            onAnswer={handleAnswer}
            disabled={isSubmitted}
          />
        ) : question.type === "case_identification" ? (
          <CaseIdentificationQuestion
            question={question}
            onAnswer={handleAnswer}
            disabled={isSubmitted}
          />
        ) : (
          <MultipleChoiceQuestion
            question={question}
            onAnswer={handleAnswer}
            disabled={isSubmitted}
          />
        )}
      </div>

      {/* Inline feedback after answering */}
      {isSubmitted && (
        <div
          className={cn(
            "flex items-center gap-2 rounded-lg px-4 py-3 text-sm",
            isCorrect ? "bg-green-500/10 text-green-300" : "bg-red-500/10 text-red-300"
          )}
        >
          {isCorrect ? (
            <CheckCircle className="h-4 w-4 shrink-0" />
          ) : (
            <XCircle className="h-4 w-4 shrink-0" />
          )}
          <span>
            {isCorrect
              ? "Correct!"
              : `Correct form: ${question.correct_form}`}
          </span>
        </div>
      )}

      {/* Next button */}
      {isSubmitted && (
        <button
          onClick={handleNext}
          className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-medium text-white
            hover:bg-blue-500 transition-colors"
        >
          {index + 1 < total ? "Next" : "See results"}
        </button>
      )}
    </div>
  )
}
